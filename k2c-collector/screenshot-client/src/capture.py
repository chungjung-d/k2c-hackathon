import io
import logging
from typing import Literal

from PIL import ImageGrab

logger = logging.getLogger(__name__)


def capture_screenshot(
    image_format: Literal["PNG", "JPEG"] = "PNG",
    quality: int = 85,
) -> bytes | None:
    """데스크톱 화면을 캡처하여 바이트 데이터로 반환한다.

    Args:
        image_format: 이미지 포맷 (PNG 또는 JPEG)
        quality: JPEG 품질 (1-100), PNG에서는 무시됨

    Returns:
        캡처된 이미지의 바이트 데이터, 실패 시 None
    """
    try:
        screenshot = ImageGrab.grab()
        buffer = io.BytesIO()

        if image_format == "JPEG":
            screenshot = screenshot.convert("RGB")
            screenshot.save(buffer, format="JPEG", quality=quality)
        else:
            screenshot.save(buffer, format="PNG")

        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        logger.error(f"스크린샷 캡처 실패: {e}")
        return None
