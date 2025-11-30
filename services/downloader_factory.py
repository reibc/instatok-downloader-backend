import logging

from config import Config
from services.base_downloader import BaseDownloader
from services.instagram_downloader import InstagramDownloader
from services.tiktok_downloader import TikTokDownloader

logger = logging.getLogger(__name__)


class DownloaderFactory:
    """Factory to get the appropriate downloader based on URL"""

    _downloaders = {
        "instagram": InstagramDownloader,
        "tiktok": TikTokDownloader,
    }

    @classmethod
    def get_downloader(cls, url: str) -> BaseDownloader:
        """
        get appropriate downloader based on URL
        """
        url_lower = url.lower()

        for platform_name in Config.SUPPORTED_PLATFORMS:
            if platform_name not in cls._downloaders:
                logger.warning(f"Platform {platform_name} not implemented")
                continue

            downloader_class = cls._downloaders[platform_name]
            downloader = downloader_class()

            if downloader.validate_url(url_lower):
                logger.info(f"Selected downloader: {platform_name}")
                return downloader

        raise ValueError(
            f"Unsupported platform. Supported platforms: {', '.join(Config.SUPPORTED_PLATFORMS)}"
        )

    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """Get list of supported platforms"""
        return list(cls._downloaders.keys())
