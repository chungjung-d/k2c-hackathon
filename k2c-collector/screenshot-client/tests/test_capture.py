import os

import pytest

from capture import capture_screenshot

# CI 환경에서는 스킵 (CI=true 환경 변수로 판단)
IS_CI = os.environ.get("CI", "false").lower() == "true"


@pytest.mark.skipif(IS_CI, reason="GUI 환경에서만 테스트 가능")
def test_capture_screenshot_png():
    """PNG 포맷으로 스크린샷이 캡처되어야 한다."""
    result = capture_screenshot(image_format="PNG")

    assert result is not None
    assert isinstance(result, bytes)
    assert result[:8] == b"\x89PNG\r\n\x1a\n"  # PNG 시그니처


@pytest.mark.skipif(IS_CI, reason="GUI 환경에서만 테스트 가능")
def test_capture_screenshot_jpeg():
    """JPEG 포맷으로 스크린샷이 캡처되어야 한다."""
    result = capture_screenshot(image_format="JPEG", quality=85)

    assert result is not None
    assert isinstance(result, bytes)
    assert result[:2] == b"\xff\xd8"  # JPEG 시그니처
