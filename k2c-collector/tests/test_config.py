import pytest

from config import Settings


def test_settings_with_required_env(monkeypatch):
    """필수 환경 변수가 설정되면 Settings가 로드되어야 한다."""
    monkeypatch.setenv("API_ENDPOINT", "http://localhost:8001/event")

    settings = Settings(_env_file=None)

    assert settings.api_endpoint == "http://localhost:8001/event"
    assert settings.capture_interval_seconds == 10
    assert settings.image_format == "PNG"
    assert settings.image_quality == 85


def test_settings_with_custom_values(monkeypatch):
    """커스텀 환경 변수가 설정되면 해당 값이 사용되어야 한다."""
    monkeypatch.setenv("API_ENDPOINT", "http://api.example.com/event")
    monkeypatch.setenv("CAPTURE_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("IMAGE_FORMAT", "jpeg")
    monkeypatch.setenv("IMAGE_QUALITY", "90")

    settings = Settings(_env_file=None)

    assert settings.api_endpoint == "http://api.example.com/event"
    assert settings.capture_interval_seconds == 30
    assert settings.image_format == "JPEG"
    assert settings.image_quality == 90


def test_settings_missing_required_env(monkeypatch):
    """필수 환경 변수가 없으면 ValidationError가 발생해야 한다."""
    monkeypatch.delenv("API_ENDPOINT", raising=False)

    with pytest.raises(Exception):
        Settings(_env_file=None)
