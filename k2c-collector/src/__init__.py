"""Screenshot Client - Desktop screenshot capture and upload client."""

from config import Settings
from capture import capture_screenshot
from upload import upload_screenshot

__all__ = ["Settings", "capture_screenshot", "upload_screenshot"]
