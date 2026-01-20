import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

import httpx

logger = logging.getLogger(__name__)


async def upload_screenshot(
    image_data: bytes,
    api_endpoint: str,
    image_format: Literal["PNG", "JPEG"] = "PNG",
    captured_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """캡처된 스크린샷을 서버 API로 전송한다.

    Args:
        image_data: 이미지 바이트 데이터
        api_endpoint: 업로드 서버 URL
        image_format: 이미지 포맷
        captured_at: 캡처 시각 (없으면 현재 시각)
        metadata: 이벤트 메타데이터

    Returns:
        업로드 성공 여부
    """
    if captured_at is None:
        captured_at = datetime.now(timezone.utc)
    elif captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)

    metadata_payload: str | None = None
    if metadata:
        try:
            metadata_payload = json.dumps(metadata, ensure_ascii=True)
        except (TypeError, ValueError) as exc:
            logger.error(f"메타데이터 직렬화 실패: {exc}")
            return False

    extension = "png" if image_format == "PNG" else "jpg"
    content_type = "image/png" if image_format == "PNG" else "image/jpeg"
    filename = f"screenshot_{captured_at.strftime('%Y%m%d_%H%M%S')}.{extension}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {"captured_at": captured_at.isoformat()}
            if metadata_payload is not None:
                data["metadata"] = metadata_payload

            files = {"image": (filename, image_data, content_type)}
            response = await client.post(api_endpoint, data=data, files=files)
            response.raise_for_status()
            logger.info(f"스크린샷 업로드 성공: {filename}")
            return True

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP 오류: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"서버 연결 실패: {e}")
        return False
