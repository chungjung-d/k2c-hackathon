# k2c-indexer

Separate indexing service for the knowledge graph.

Entry points:
- `k2c-indexer-server`: FastAPI server to enqueue indexing jobs.
- `k2c-indexer-agent`: background worker that upserts to Neo4j.

The agent runs 5 parallel groups of 5 peer agents (max 3 rounds per group) to decide graph
placement and can query Neo4j before writing. It uses `OPENAI_API_KEY` and
`OPENAI_INDEXER_MODEL` (defaults to `gpt-5-mini`, falls back to `OPENAI_MODEL` if unset).
It can also be started inside the server process by setting `INDEXER_RUN_AGENT=1`.
Each graph write should include the Postgres job id as `origin_job_id` and as a tag
(`origin:<id>`).

Configuration comes from environment variables (see root `fnox.toml`).
Infra services run via the root `docker-compose.yaml`.

HTTP tests (httpyac):
```
mise task indexer.test.http
```
