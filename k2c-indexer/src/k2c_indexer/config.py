from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="k2cneo4j", alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    agent_interval_seconds: int = Field(default=20, alias="AGENT_INTERVAL_SECONDS")
    indexer_server_port: int = Field(default=8003, alias="INDEXER_SERVER_PORT")
    run_agent_in_server: bool = Field(default=False, alias="INDEXER_RUN_AGENT")
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str | None = Field(default=None, alias="OPENAI_MODEL")
    env: str = Field(default="local", alias="ENV")

    model_config = SettingsConfigDict(env_file=None, extra="ignore")


settings = Settings()
