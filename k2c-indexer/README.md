# k2c-indexer

Separate indexing service for the knowledge graph.

Entry points:
- `k2c-indexer-server`: FastAPI server to enqueue indexing jobs.
- `k2c-indexer-agent`: background worker that upserts to Neo4j.

The agent runs 5 peer agents in a group chat (max 5 rounds) to decide graph placement and can
query Neo4j before writing. It uses `OPENAI_API_KEY` (and optional `OPENAI_MODEL`).
It can also be started inside the server process by setting `INDEXER_RUN_AGENT=1`.
Each graph write should include the Postgres job id as `origin_job_id` and as a tag
(`origin:<id>`).

Configuration comes from environment variables (see root `fnox.toml`).
Infra services run via the root `docker-compose.yaml`.
