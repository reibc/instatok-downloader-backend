import logging
import os

from config import Config
from services.base_downloader import BaseDownloader
from services.instagram_alternative_downloader import \
    InstagramAlternativeDownloader
from services.instagram_downloader import InstagramDownloader
from services.tiktok_downloader import TikTokDownloader

logger = logging.getLogger(__name__)


class DownloaderFactory:
    """Factory to get the appropriate downloader based on URL"""

    _downloaders = {
        "instagram": InstagramDownloader,
        "instagram_alt": InstagramAlternativeDownloader,
        "tiktok": TikTokDownloader,
    }

    @classmethod
    def get_downloader(cls, url: str) -> BaseDownloader:
        """
        get appropriate downloader based on URL
        """
        url_lower = url.lower()

        use_alt_instagram = os.getenv("USE_ALT_INSTAGRAM", "false").lower() == "true"

        for platform_name in Config.SUPPORTED_PLATFORMS:
            if platform_name not in ["instagram", "tiktok"]:
                logger.warning(f"Platform {platform_name} not implemented")
                continue

            if platform_name == "instagram":
                if "instagram.com" in url_lower:
                    if use_alt_instagram:
                        logger.info("Using alternative Instagram downloader (FastDL)")
                        return InstagramAlternativeDownloader()
                    else:
                        logger.info("Using standard Instagram downloader")
                        return InstagramDownloader()

            if platform_name in cls._downloaders:
                downloader_class = cls._downloaders[platform_name]
                downloader = downloader_class()

                if downloader.validate_url(url):
                    logger.info(f"Selected downloader: {platform_name}")
                    return downloader

        raise ValueError(
            f"Unsupported platform. Supported platforms: {', '.join(Config.SUPPORTED_PLATFORMS)}"
        )

    @classmethod
    def get_supported_platforms(cls) -> list[str]:
        """Get list of supported platforms"""
        return ["instagram", "tiktok"]
