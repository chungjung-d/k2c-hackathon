from enum import Enum
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ImageFormat(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"


class Settings(BaseSettings):
    api_endpoint: str = Field(..., description="스크린샷 업로드 서버 URL")
    capture_interval_seconds: int = Field(default=10, description="캡처 간격 (초)")
    image_format: Literal["PNG", "JPEG"] = Field(
        default="PNG", description="이미지 포맷"
    )
    image_quality: int = Field(
        default=85, ge=1, le=100, description="JPEG 품질 (1-100)"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("image_format", mode="before")
    @classmethod
    def normalize_image_format(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if normalized == "JPG":
            normalized = "JPEG"
        return normalized
