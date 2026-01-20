from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from concurrent.futures import ThreadPoolExecutor, as_completed

from agents import Agent, Runner, function_tool
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from .config import settings
from .db import execute, execute_returning, fetch_all

logger = logging.getLogger(__name__)

PENDING_JOBS_QUERY = """
SELECT id, raw_request, payload
FROM index_jobs
WHERE status = 'pending'
ORDER BY enqueued_at ASC
LIMIT %s
"""

CLAIM_JOB_QUERY = """
UPDATE index_jobs
SET status = 'processing', processed_at = NULL
WHERE id = %s AND status = 'pending'
RETURNING id
"""

GROUP_COUNT = 5
MAX_GROUP_ROUNDS = 3


class PeerResponse(BaseModel):
    message: str
    continue_discussion: bool = True


class GraphPlan(BaseModel):
    cypher: str
    params: dict[str, Any] = Field(default_factory=dict)
    verification_queries: list[str] = Field(default_factory=list)
    notes: str | None = None


def _build_agent(
    name: str,
    instructions: str,
    output_type: type[Any] | None = None,
    tools: list | None = None,
) -> Agent:
    kwargs: dict[str, Any] = {
        "name": name,
        "instructions": instructions,
        "output_type": output_type,
    }
    if tools:
        kwargs["tools"] = tools
    model = settings.openai_indexer_model or settings.openai_model
    if model:
        kwargs["model"] = model
    return Agent(**kwargs)


def _driver() -> GraphDatabase:
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


@function_tool(strict_mode=False)
def cypher_read(
    query: str, parameters: dict[str, Any] | None = None, limit: int = 25
) -> dict[str, Any]:
    driver = _driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(query, parameters or {})
        records = [record.data() for record in result][:limit]
    driver.close()
    return {"records": records}


def _execute_cypher(query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    logger.info("Executing cypher write")
    driver = _driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(query, parameters or {})
        summary = result.consume()
    driver.close()
    counters = summary.counters
    return {
        "nodes_created": counters.nodes_created,
        "nodes_deleted": counters.nodes_deleted,
        "relationships_created": counters.relationships_created,
        "relationships_deleted": counters.relationships_deleted,
        "properties_set": counters.properties_set,
        "labels_added": counters.labels_added,
    }


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        sanitized = []
        for item in value:
            if isinstance(item, dict):
                sanitized.append(json.dumps(item, ensure_ascii=True))
            else:
                sanitized.append(_sanitize_value(item))
        return sanitized
    return value


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    return {key: _sanitize_value(value) for key, value in params.items()}


def _default_plan(payload: dict, origin_job_id: str) -> GraphPlan:
    event = payload.get("event") or {}
    features = payload.get("features") or {}
    tags = features.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tags = [str(tag) for tag in tags if tag is not None]
    tags.append(f"origin:{origin_job_id}")

    event_id = event.get("id")
    if not event_id:
        raise ValueError("index payload missing event.id")

    params = {
        "event_id": event_id,
        "user_id": event.get("user_id") or "unknown",
        "captured_at": event.get("captured_at"),
        "object_key": event.get("object_key"),
        "content_type": event.get("content_type"),
        "size_bytes": event.get("size_bytes"),
        "sha256": event.get("sha256"),
        "summary": features.get("summary"),
        "content_summary": features.get("content_summary"),
        "user_activity": features.get("user_activity"),
        "risk_level": features.get("risk_level"),
        "ocr_text": features.get("ocr_text"),
        "metadata": features.get("metadata"),
        "tags": tags,
        "origin_job_id": origin_job_id,
    }

    cypher = """
    MERGE (u:User {id: $user_id})
    MERGE (e:ScreenshotEvent {event_id: $event_id})
    SET e.captured_at = $captured_at,
        e.object_key = $object_key,
        e.content_type = $content_type,
        e.size_bytes = $size_bytes,
        e.sha256 = $sha256,
        e.summary = $summary,
        e.content_summary = $content_summary,
        e.user_activity = $user_activity,
        e.risk_level = $risk_level,
        e.ocr_text = $ocr_text,
        e.metadata = $metadata,
        e.origin_job_id = $origin_job_id,
        e.updated_at = timestamp()
    MERGE (u)-[:CAPTURED]->(e)
    FOREACH (tag IN $tags |
        MERGE (t:Tag {name: tag})
        MERGE (e)-[:HAS_TAG]->(t)
    )
    """
    return GraphPlan(cypher=cypher, params=params, notes="fallback plan")


def _build_peer_group(group_id: int) -> list[Agent]:
    return [
        _build_agent(
            name=f"G{group_id}-GraphPlanner",
            instructions=(
                "You are a peer in a group chat designing a Neo4j knowledge graph layout. "
                "Review the payload and propose node/relationship placement. "
                "Use cypher_read to inspect the current graph if needed. "
                "Check for conflicts with existing nodes and suggest merges. "
                "Keep responses concise and actionable."
            ),
            output_type=PeerResponse,
            tools=[cypher_read],
        ),
        _build_agent(
            name=f"G{group_id}-GraphCritic",
            instructions=(
                "You are a peer reviewer in a group chat. "
                "Critique the proposed graph layout, check for missing relationships, "
                "and suggest improvements. Use cypher_read to verify assumptions."
            ),
            output_type=PeerResponse,
            tools=[cypher_read],
        ),
        _build_agent(
            name=f"G{group_id}-SchemaLibrarian",
            instructions=(
                "You are a peer focused on schema consistency. "
                "Ensure node labels, relationship types, and properties are stable. "
                "Recommend normalization or taxonomy changes when needed. "
                "Use cypher_read to inspect existing labels."
            ),
            output_type=PeerResponse,
            tools=[cypher_read],
        ),
        _build_agent(
            name=f"G{group_id}-QueryStrategist",
            instructions=(
                "You are a peer focused on queryability. "
                "Suggest structure that supports likely KG queries and analytics. "
                "Use cypher_read to verify existing patterns."
            ),
            output_type=PeerResponse,
            tools=[cypher_read],
        ),
        _build_agent(
            name=f"G{group_id}-RiskObserver",
            instructions=(
                "You are a peer focused on data risks and leakage. "
                "Flag sensitive properties and suggest safer placement/omission. "
                "Use cypher_read to check what is already stored."
            ),
            output_type=PeerResponse,
            tools=[cypher_read],
        ),
    ]


def _run_peer_group(
    group_id: int, payload: dict, raw_request: dict, origin_job_id: str
) -> list[dict[str, str]]:
    peers = _build_peer_group(group_id)
    discussion: list[dict[str, str]] = []

    for round_index in range(MAX_GROUP_ROUNDS):
        logger.info(
            "Group %s chat round %s for job %s",
            group_id,
            round_index + 1,
            origin_job_id,
        )
        should_continue = False
        for agent in peers:
            prompt = json.dumps(
                {
                    "round": round_index + 1,
                    "payload": payload,
                    "raw_request": raw_request,
                    "origin_job_id": origin_job_id,
                    "discussion": discussion,
                },
                ensure_ascii=True,
            )
            result = Runner.run_sync(agent, prompt)
            output = result.final_output
            if not isinstance(output, PeerResponse):
                output = PeerResponse.model_validate(output)
            discussion.append({"role": agent.name, "content": output.message})
            logger.info("Peer %s responded for job %s", agent.name, origin_job_id)
            should_continue = should_continue or output.continue_discussion
        if not should_continue:
            break

    return discussion


def _run_group_chat(payload: dict, raw_request: dict, origin_job_id: str) -> GraphPlan | None:
    if not settings.openai_api_key:
        return None
    try:
        discussion: list[dict[str, str]] = []
        with ThreadPoolExecutor(max_workers=GROUP_COUNT) as executor:
            futures = [
                executor.submit(_run_peer_group, group_id, payload, raw_request, origin_job_id)
                for group_id in range(1, GROUP_COUNT + 1)
            ]
            for future in as_completed(futures):
                discussion.extend(future.result())

        executor = _build_agent(
            name="GraphExecutor",
            instructions=(
                "You are the final peer. Using the payload and discussion, "
                "produce a single Cypher upsert plan with parameters. "
                "Use cypher_read if you need to verify existing nodes. "
                "You may split data across multiple nodes and update existing nodes. "
                "Check for conflicts with existing nodes (e.g., same event_id). "
                "Include origin_job_id as a property on each new/updated node, and "
                "also add it as a tag (e.g., origin:<id>) on relevant tag lists. "
                "Return JSON matching the output schema."
            ),
            output_type=GraphPlan,
            tools=[cypher_read],
        )

        plan_prompt = json.dumps(
            {
                "payload": payload,
                "raw_request": raw_request,
                "origin_job_id": origin_job_id,
                "discussion": discussion,
            },
            ensure_ascii=True,
        )
        result = Runner.run_sync(executor, plan_prompt)
        output = result.final_output
        if isinstance(output, GraphPlan):
            return output
        return GraphPlan.model_validate(output)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Group chat planning failed: %s", exc)
        return None


def _mark_done(job_id: str) -> None:
    execute(
        "UPDATE index_jobs SET status = %s, processed_at = %s WHERE id = %s",
        ("done", datetime.now(timezone.utc), job_id),
    )


def _mark_error(job_id: str, error: str) -> None:
    execute(
        "UPDATE index_jobs SET status = %s, processed_at = %s, last_error = %s WHERE id = %s",
        ("error", datetime.now(timezone.utc), error[:500], job_id),
    )


def _claim_job(job_id: str) -> bool:
    row = execute_returning(CLAIM_JOB_QUERY, (job_id,))
    return bool(row)


def run_loop() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    logger.info(
        "Starting indexer agent (interval=%ss, group_count=%s, group_rounds=%s)",
        settings.agent_interval_seconds,
        GROUP_COUNT,
        MAX_GROUP_ROUNDS,
    )
    while True:
        jobs = fetch_all(PENDING_JOBS_QUERY, (10,))
        if not jobs:
            time.sleep(settings.agent_interval_seconds)
            continue
        for job in jobs:
            job_id = str(job["id"])
            if not _claim_job(job_id):
                continue
            logger.info("Claimed index job %s", job_id)
            raw_request = job.get("raw_request") or {}
            if isinstance(raw_request, str):
                raw_request = json.loads(raw_request)
            payload = job.get("payload") or raw_request
            if isinstance(payload, str):
                payload = json.loads(payload)
            try:
                logger.info("Planning graph update for job %s", job_id)
                plan = _run_group_chat(payload, raw_request, job_id) or _default_plan(
                    payload, job_id
                )
                logger.info(
                    "Applying graph plan for job %s (notes=%s)", job_id, plan.notes
                )
                sanitized_params = _sanitize_params(plan.params)
                if sanitized_params != plan.params:
                    logger.info(
                        "Sanitized params for job %s (non-primitive properties converted)",
                        job_id,
                    )
                _execute_cypher(plan.cypher, sanitized_params)
                for query in plan.verification_queries:
                    cypher_read(query)
                _mark_done(job_id)
                logger.info("Indexed job %s", job_id)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to index job %s", job_id)
                _mark_error(job_id, str(exc))
        time.sleep(1)


def run() -> None:
    run_loop()


if __name__ == "__main__":
    run()
