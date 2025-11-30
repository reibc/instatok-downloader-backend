import logging
import re
from io import BytesIO

import instaloader
import requests

from services.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseDownloader):
    def __init__(self):
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )

    @property
    def platform_name(self) -> str:
        return "instagram"

    def validate_url(self, url: str) -> bool:
        return any(domain in url.lower() for domain in ["instagram.com"])

    def extract_video_id(self, url: str) -> str:
        """
        Extract shortcode from Instagram URL
        """
        url = url.split("?")[0]

        url = url.rstrip("/")

        match = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)

        url_parts = url.split("/")
        shortcode = url_parts[-1] if url_parts[-1] else url_parts[-2]

        return shortcode

    def get_video_stream(self, url: str) -> tuple[BytesIO, str, str]:
        """Download Instagram reel/video"""
        logger.info(f"[Instagram] Getting video stream for: {url}")

        shortcode = self.extract_video_id(url)
        logger.info(f"[Instagram] Extracted shortcode: {shortcode}")

        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            if not post.is_video:
                raise ValueError("This post is not a video")

            video_url = post.video_url
            logger.info(f"[Instagram] Video URL: {video_url}")

            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()

            video_data = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    video_data.write(chunk)

            video_data.seek(0)

            file_size_mb = len(video_data.getvalue()) / (1024 * 1024)
            logger.info(
                f"[Instagram] Video streamed: {shortcode} ({file_size_mb:.2f} MB)"
            )

            filename = f"instagram_{shortcode}.mp4"

            return video_data, shortcode, filename

        except Exception as e:
            logger.error(f"[Instagram] Error: {str(e)}")
            raise ValueError(f"Failed to download Instagram video: {str(e)}")

    def get_video_url(self, url: str) -> tuple[str, str]:
        shortcode = self.extract_video_id(url)
        post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

        if not post.is_video:
            raise ValueError("This post is not a video")

        return post.video_url, shortcode
