import logging
import os
import re
import time
from io import BytesIO

import requests

from services.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class InstagramAlternativeDownloader(BaseDownloader):
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        self.rapidapi_host = "instagram-reels-downloader-api.p.rapidapi.com"
        self.api_url = f"https://{self.rapidapi_host}/download"
        self.last_request_time = 0
        self.min_request_interval = 1

    @property
    def platform_name(self) -> str:
        return "instagram"

    def validate_url(self, url: str) -> bool:
        return any(domain in url.lower() for domain in ["instagram.com"])

    def extract_video_id(self, url: str) -> str:
        url = url.split("?")[0].rstrip("/")
        match = re.search(r"/(?:reel|p|tv)/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        url_parts = url.split("/")
        return url_parts[-1] if url_parts[-1] else url_parts[-2]

    def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_video_stream(self, url: str) -> tuple[BytesIO, str, str]:
        """Download Instagram video using RapidAPI"""
        logger.info(f"[Instagram RapidAPI] Getting video stream for: {url}")

        if not self.rapidapi_key:
            raise ValueError(
                "RAPIDAPI_KEY not configured. "
                "Sign up at https://rapidapi.com and subscribe to Instagram Reels Downloader API"
            )

        self._rate_limit()

        shortcode = self.extract_video_id(url)
        logger.info(f"[Instagram RapidAPI] Extracted shortcode: {shortcode}")

        try:
            querystring = {"url": url}

            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": self.rapidapi_host,
            }

            logger.info(f"[Instagram RapidAPI] Calling API...")
            response = requests.get(
                self.api_url, headers=headers, params=querystring, timeout=30
            )

            if response.status_code == 403:
                error_data = response.json() if response.content else {}
                if "not subscribed" in error_data.get("message", "").lower():
                    raise ValueError(
                        "Not subscribed to RapidAPI. "
                        "Please visit https://rapidapi.com/easeapi-easeapi-default/api/instagram-reels-downloader-api "
                        "and subscribe to the FREE plan"
                    )

            response.raise_for_status()

            data = response.json()
            logger.info(f"[Instagram RapidAPI] API response received")

            if not data.get("success"):
                error_msg = data.get("message", "Unknown error")
                raise ValueError(f"API returned error: {error_msg}")

            api_data = data.get("data", {})

            if not api_data:
                raise ValueError("No data in API response")

            medias = api_data.get("medias", [])

            video_url = None
            for media in medias:
                if media.get("type") == "video":
                    video_url = media.get("url")
                    quality = media.get("quality", "unknown")
                    logger.info(f"[Instagram RapidAPI] Found video: {quality}")
                    break

            if not video_url:
                raise ValueError("No video URL found in API response")

            logger.info(f"[Instagram RapidAPI] Video URL extracted")

            logger.info(f"[Instagram RapidAPI] Downloading video...")
            video_response = requests.get(
                video_url,
                stream=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                timeout=60,
            )
            video_response.raise_for_status()

            video_data = BytesIO()
            for chunk in video_response.iter_content(chunk_size=8192):
                if chunk:
                    video_data.write(chunk)

            video_data.seek(0)

            file_size_mb = len(video_data.getvalue()) / (1024 * 1024)
            logger.info(
                f"[Instagram RapidAPI] Video downloaded: {shortcode} ({file_size_mb:.2f} MB)"
            )

            filename = f"instagram_{shortcode}.mp4"

            return video_data, shortcode, filename

        except requests.exceptions.HTTPError as e:
            error_text = e.response.text[:500] if e.response.content else str(e)
            logger.error(
                f"[Instagram RapidAPI] HTTP Error: {e.response.status_code} - {error_text}"
            )

            if e.response.status_code == 403:
                raise ValueError(
                    "API subscription required. "
                    "Visit https://rapidapi.com/easeapi-easeapi-default/api/instagram-reels-downloader-api "
                    "and subscribe to the FREE plan (100 requests/day)"
                )

            raise ValueError(f"RapidAPI request failed: {str(e)}")

        except Exception as e:
            logger.error(f"[Instagram RapidAPI] Error: {str(e)}")
            raise ValueError(
                f"Failed to download Instagram video via RapidAPI: {str(e)}"
            )

    def get_video_url(self, url: str) -> tuple[str, str]:
        shortcode = self.extract_video_id(url)

        try:
            querystring = {"url": url}

            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": self.rapidapi_host,
            }

            response = requests.get(
                self.api_url, headers=headers, params=querystring, timeout=30
            )
            response.raise_for_status()

            data = response.json()

            if data.get("success") and data.get("data"):
                medias = data["data"].get("medias", [])
                for media in medias:
                    if media.get("type") == "video":
                        return media.get("url", ""), shortcode

            return "", shortcode

        except Exception as e:
            logger.error(f"[Instagram RapidAPI] Error getting video URL: {str(e)}")
            return "", shortcode
