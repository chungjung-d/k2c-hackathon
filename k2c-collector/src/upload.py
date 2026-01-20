import logging
from datetime import datetime
from typing import Literal

import httpx

logger = logging.getLogger(__name__)


async def upload_screenshot(
    image_data: bytes,
    api_endpoint: str,
    image_format: Literal["PNG", "JPEG"] = "PNG",
) -> bool:
    """캡처된 스크린샷을 서버 API로 전송한다.

    Args:
        image_data: 이미지 바이트 데이터
        api_endpoint: 업로드 서버 URL
        image_format: 이미지 포맷

    Returns:
        업로드 성공 여부
    """
    extension = "png" if image_format == "PNG" else "jpg"
    content_type = "image/png" if image_format == "PNG" else "image/jpeg"
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (filename, image_data, content_type)}
            response = await client.post(api_endpoint, files=files)
            response.raise_for_status()
            logger.info(f"스크린샷 업로드 성공: {filename}")
            return True

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP 오류: {e.response.status_code} - {e.response.text}")
        return False
    except httpx.RequestError as e:
        logger.error(f"서버 연결 실패: {e}")
        return False
