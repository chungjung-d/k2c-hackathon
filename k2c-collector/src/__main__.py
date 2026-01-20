import asyncio
import logging
import sys
from datetime import datetime, timezone

from capture import capture_screenshot
from config import Settings
from upload import upload_screenshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ScreenshotScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._current_task: asyncio.Task | None = None

    async def _capture_and_upload(self) -> None:
        """스크린샷을 캡처하고 서버로 업로드한다."""
        captured_at = datetime.now(timezone.utc)
        image_data = capture_screenshot(
            image_format=self.settings.image_format,
            quality=self.settings.image_quality,
        )
        if image_data:
            await upload_screenshot(
                image_data=image_data,
                api_endpoint=self.settings.api_endpoint,
                image_format=self.settings.image_format,
                captured_at=captured_at,
                metadata={"source": "k2c-collector"},
            )

    async def run(self) -> None:
        """주기적으로 스크린샷을 캡처하고 업로드한다."""
        logger.info(
            f"스크린샷 스케줄러 시작 (간격: {self.settings.capture_interval_seconds}초)"
        )

        while True:
            self._current_task = asyncio.create_task(self._capture_and_upload())
            try:
                await self._current_task
            except asyncio.CancelledError:
                break

            try:
                await asyncio.sleep(self.settings.capture_interval_seconds)
            except asyncio.CancelledError:
                break

        logger.info("스크린샷 스케줄러 종료")


async def main() -> None:
    try:
        settings = Settings()
    except Exception as e:
        logger.error(f"설정 로드 실패: {e}")
        sys.exit(1)

    scheduler = ScreenshotScheduler(settings)
    await scheduler.run()


if __name__ == "__main__":
    asyncio.run(main())
