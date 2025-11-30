import logging
import re
from io import BytesIO

import requests

from services.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class TikTokDownloader(BaseDownloader):
    @property
    def platform_name(self) -> str:
        return "tiktok"

    def validate_url(self, url: str) -> bool:
        """Check if URL is from TikTok"""
        return any(domain in url.lower() for domain in ["tiktok.com", "vm.tiktok.com"])

    def extract_video_id(self, url: str) -> str:
        """Extract video ID from TikTok URL"""
        match = re.search(r"/video/(\d+)", url)
        if match:
            return match.group(1)
        return url.split("/")[-1].split("?")[0]

    def get_video_stream(self, url: str) -> tuple[BytesIO, str, str]:
        """
        Download TikTok video
        """
        logger.info(f"[TikTok] Getting video stream for: {url}")

        video_id = self.extract_video_id(url)

        try:
            api_url = "https://www.tikwm.com/api/"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            response = requests.post(
                api_url, headers=headers, data={"url": url}, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 0:
                raise ValueError(f"API error: {data.get('msg', 'Unknown error')}")

            video_url = data["data"]["play"]

            logger.info(f"[TikTok] Got download URL from API")

            video_response = requests.get(
                video_url, stream=True, headers=headers, timeout=30
            )
            video_response.raise_for_status()

            video_data = BytesIO()
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    video_data.write(chunk)

            video_data.seek(0)

            file_size_mb = len(video_data.getvalue()) / (1024 * 1024)
            logger.info(f"[TikTok] Video streamed: {video_id} ({file_size_mb:.2f} MB)")

            filename = f"tiktok_{video_id}.mp4"

            return video_data, video_id, filename

        except Exception as e:
            logger.error(f"[TikTok] Error: {str(e)}")
            raise ValueError(
                f"TikTok download failed. TikTok frequently blocks automated downloads. Error: {str(e)}"
            )

    def get_video_url(self, url: str) -> tuple[str, str]:
        video_id = self.extract_video_id(url)

        try:
            api_url = "https://www.tikwm.com/api/"
            response = requests.post(api_url, data={"url": url}, timeout=30)
            data = response.json()

            if data.get("code") != 0:
                raise ValueError("API error")

            return data["data"]["play"], video_id
        except Exception as e:
            raise ValueError(f"Failed to get TikTok URL: {str(e)}")
