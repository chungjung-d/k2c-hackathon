import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import httpx

from upload import upload_screenshot


@pytest.mark.asyncio
async def test_upload_screenshot_success():
    """스크린샷 업로드가 성공해야 한다."""
    image_data = b"fake_image_data"
    api_endpoint = "http://localhost:8001/event"
    captured_at = datetime(2025, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
    metadata = {"source": "test-suite"}

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    with patch("upload.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await upload_screenshot(
            image_data=image_data,
            api_endpoint=api_endpoint,
            image_format="PNG",
            captured_at=captured_at,
            metadata=metadata,
        )

    assert result is True
    mock_client.post.assert_called_once()
    _, kwargs = mock_client.post.call_args
    assert kwargs["data"]["captured_at"] == captured_at.isoformat()
    assert kwargs["data"]["metadata"] == json.dumps(metadata, ensure_ascii=True)
    assert "image" in kwargs["files"]


@pytest.mark.asyncio
async def test_upload_screenshot_connection_error():
    """서버 연결 실패 시 False를 반환해야 한다."""
    image_data = b"fake_image_data"
    api_endpoint = "http://invalid-host.local:9999/event"

    result = await upload_screenshot(
        image_data=image_data,
        api_endpoint=api_endpoint,
        image_format="PNG",
    )

    assert result is False
