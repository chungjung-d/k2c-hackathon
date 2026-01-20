# k2c-agents

Backend services and background agents for the k2c hackathon pipeline.

Entry points:
- `k2c-preprocess-server`: FastAPI server handling `POST /event`.
- `k2c-preprocess-agent`: background feature extractor.
- `k2c-eval-agent`: background evaluator.
- `k2c-lead-agent`: lead agent session/CLI to coordinate goals and update config.
- `k2c-lead-server`: lead agent HTTP server for goal conversations.

Configuration comes from environment variables (see `fnox.toml`).
