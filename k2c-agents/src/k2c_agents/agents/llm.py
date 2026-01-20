from __future__ import annotations

import json
import logging
from typing import Any

from agents import Agent, Runner
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)


class FeatureSummary(BaseModel):
    summary: str
    tags: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"


class EvaluationSummary(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    labels: list[str] = Field(default_factory=list)


def _build_agent(name: str, instructions: str, output_type: type[BaseModel]) -> Agent:
    if settings.openai_model:
        return Agent(
            name=name,
            instructions=instructions,
            output_type=output_type,
            model=settings.openai_model,
        )
    return Agent(name=name, instructions=instructions, output_type=output_type)


def summarize_event(metadata: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    if not settings.openai_api_key:
        return {
            "summary": "LLM disabled; stored metadata only.",
            "tags": [],
            "risk_level": "unknown",
            "source": "fallback",
        }

    agent = _build_agent(
        name="FeatureExtractor",
        instructions=(
            "You are extracting compact features from screenshot metadata. "
            "Return concise summaries and short tags. If you are unsure, say so briefly."
        ),
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
