# k2c-agents

Backend services and background agents for the k2c hackathon pipeline.

Entry points:
- `k2c-collector-proxy`: FastAPI server handling `POST /event` (renamed from preprocess server).
- `k2c-preprocess-agent`: background OCR/feature extractor that forwards `raw_data` and `processed_data` JSON to the indexer.

Configuration comes from environment variables (see `fnox.toml`). Infra services run via
the root `docker-compose.yaml`.
