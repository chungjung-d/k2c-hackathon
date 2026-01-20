# k2c-agents

Backend services and background agents for the k2c hackathon pipeline.

Entry points:
- `k2c-preprocess-server`: FastAPI server handling `POST /event`.
- `k2c-preprocess-agent`: background feature extractor.
- `k2c-eval-agent`: background evaluator.
- `k2c-lead-agent`: helper to update goals/config.

Configuration comes from environment variables (see `fnox.toml`).
