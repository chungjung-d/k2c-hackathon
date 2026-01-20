# k2c-indexer

Separate indexing service for the knowledge graph.

Entry points:
- `k2c-indexer-server`: FastAPI server to enqueue indexing jobs.
- `k2c-indexer-agent`: background worker that upserts to Neo4j.

The agent runs 5 peer agents in a group chat (max 5 rounds) to decide graph placement and can
query Neo4j before writing. It uses `OPENAI_API_KEY` (and optional `OPENAI_MODEL`).

Configuration comes from environment variables (see root `fnox.toml`).
