from __future__ import annotations

import base64
import json
import logging
from typing import Annotated, Any

from agents import Agent, Runner, ToolOutputImage, function_tool
from pydantic import BaseModel, Field

from ..config import settings
from ..storage import get_bytes

logger = logging.getLogger(__name__)


class FeatureSummary(BaseModel):
    summary: str
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"


class EvaluationSummary(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    labels: list[str] = Field(default_factory=list)


class ScreenshotFeatureSummary(BaseModel):
    ocr_text: str = ""
    content_summary: str = ""
    user_activity: str = ""
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"


def _build_agent(
    name: str,
    instructions: str,
    output_type: type[BaseModel],
    tools: list | None = None,
) -> Agent:
    kwargs = {
        "name": name,
        "instructions": instructions,
        "output_type": output_type,
    }
    if tools:
        kwargs["tools"] = tools
    if settings.openai_model:
        kwargs["model"] = settings.openai_model
    return Agent(**kwargs)


def summarize_event(
    metadata: dict[str, Any], extra: dict[str, Any], goal: str | None = None
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "summary": "LLM disabled; stored metadata only.",
            "tags": [],
            "risk_level": "unknown",
            "source": "fallback",
        }

    instructions = (
        "You are extracting compact features from screenshot metadata. "
        "Return concise summaries and short tags. If you are unsure, say so briefly."
    )
    if goal:
        instructions += f" Use this preprocessing goal: {goal}."
    agent = _build_agent(
        name="FeatureExtractor",
        instructions=instructions,
        output_type=FeatureSummary,
    )

    payload = json.dumps({"metadata": metadata, "extra": extra}, ensure_ascii=True)
    try:
        result = Runner.run_sync(agent, payload)
        output = result.final_output
        if isinstance(output, FeatureSummary):
            data = output.model_dump()
        else:
            data = FeatureSummary.model_validate(output).model_dump()
        data["source"] = "llm"
        return data
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Feature extraction failed: %s", exc)
        return {
            "summary": "LLM failure; stored metadata only.",
            "tags": [],
            "risk_level": "unknown",
            "source": "error",
        }


@function_tool
def fetch_screenshot(
    s3_key: Annotated[str, "S3 key for the screenshot object"],
    content_type: Annotated[str, "MIME type of the image (e.g., image/png)"],
) -> ToolOutputImage:
    image_bytes = get_bytes(s3_key)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{content_type};base64,{image_base64}"
    return ToolOutputImage(image_url=image_url, detail="high")


def analyze_screenshot(
    s3_key: str,
    content_type: str,
    metadata: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "ocr_text": "",
            "content_summary": "LLM disabled; OCR unavailable.",
            "user_activity": "unknown",
            "tags": [],
            "risk_level": "unknown",
            "source": "fallback",
            "ocr_source": "fallback",
        }

    agent = _build_agent(
        name="ScreenshotAnalyzer",
        instructions=(
            "You analyze screenshots from S3. Input is JSON with s3_key, content_type, "
            "metadata, and extra. First call fetch_screenshot with s3_key and content_type. "
            "Then read the image and extract ALL visible text verbatim into ocr_text. "
            "Provide content_summary (1-2 sentences) describing what the content is about. "
            "Provide user_activity (1 sentence) describing what the user is doing. "
            "If text is not readable, set ocr_text to an empty string."
        ),
        output_type=ScreenshotFeatureSummary,
        tools=[fetch_screenshot],
    )

    payload = json.dumps(
        {
            "s3_key": s3_key,
            "content_type": content_type,
            "metadata": metadata,
            "extra": extra,
        },
        ensure_ascii=True,
    )
    try:
        result = Runner.run_sync(agent, payload)
        output = result.final_output
        if isinstance(output, ScreenshotFeatureSummary):
            data = output.model_dump()
        else:
            data = ScreenshotFeatureSummary.model_validate(output).model_dump()
        data["source"] = "llm"
        data["ocr_source"] = "vision"
        return data
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Screenshot analysis failed: %s", exc)
        return {
            "ocr_text": "",
            "content_summary": "LLM failure; OCR unavailable.",
            "user_activity": "unknown",
            "tags": [],
            "risk_level": "unknown",
            "source": "error",
            "ocr_source": "error",
        }


def evaluate_features(goal: str, features: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "score": 0,
            "summary": "LLM disabled; no evaluation performed.",
            "labels": ["unscored"],
            "source": "fallback",
        }

    agent = _build_agent(
        name="FeatureEvaluator",
        instructions=(
            "Evaluate extracted screenshot features against the current goal. "
            "Return an integer score (0-100) and a short summary with labels."
        ),
        output_type=EvaluationSummary,
    )

    payload = json.dumps({"goal": goal, "features": features}, ensure_ascii=True)
    try:
        result = Runner.run_sync(agent, payload)
        output = result.final_output
        if isinstance(output, EvaluationSummary):
            data = output.model_dump()
        else:
            data = EvaluationSummary.model_validate(output).model_dump()
        data["source"] = "llm"
        return data
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Evaluation failed: %s", exc)
        return {
            "score": 0,
            "summary": "LLM failure; evaluation unavailable.",
            "labels": ["error"],
            "source": "error",
        }
