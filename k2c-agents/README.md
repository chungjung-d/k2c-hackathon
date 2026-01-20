# k2c-agents

Backend services and background agents for the k2c hackathon pipeline.

Entry points:
- `k2c-preprocess-server`: FastAPI server handling `POST /event`.
- `k2c-preprocess-agent`: background feature extractor.

Configuration comes from environment variables (see `fnox.toml`).
