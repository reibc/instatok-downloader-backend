import logging
import re
import time
from io import BytesIO

import instaloader
import requests

from services.base_downloader import BaseDownloader
from services.proxy_manager import proxy_manager

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
        self.last_request_time = 0
        self.min_request_interval = 3
        self.max_retries = 3

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

    def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"[Instagram] Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _setup_session_with_proxy(self, session):
        """Configure instaloader session to use proxy"""
        proxy = proxy_manager.get_working_proxy()

        if proxy:
            logger.info("[Instagram] Using proxy for instaloader session")
            proxy_url = proxy.get("http", "").replace("http://", "")
            session.proxies = {
                "http": f"http://{proxy_url}",
                "https": f"http://{proxy_url}",
            }
            logger.info(f"[Instagram] Proxy configured: {proxy_url}")
        else:
            logger.info(
                "[Instagram] No working proxy available, using direct connection"
            )

    def get_video_stream(self, url: str) -> tuple[BytesIO, str, str]:
        """Download Instagram reel/video with proxy support"""
        logger.info(f"[Instagram] Getting video stream for: {url}")

        self._rate_limit()

        shortcode = self.extract_video_id(url)
        logger.info(f"[Instagram] Extracted shortcode: {shortcode}")

        for attempt in range(self.max_retries):
            try:
                self._setup_session_with_proxy(self.loader.context._session)

                post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

                if not post.is_video:
                    raise ValueError("This post is not a video")

                video_url = post.video_url
                logger.info(f"[Instagram] Video URL obtained")

                video_data = self._download_video_with_proxy(video_url)

                file_size_mb = len(video_data.getvalue()) / (1024 * 1024)
                logger.info(
                    f"[Instagram] Video streamed: {shortcode} ({file_size_mb:.2f} MB)"
                )

                filename = f"instagram_{shortcode}.mp4"

                return video_data, shortcode, filename

            except instaloader.exceptions.ConnectionException as e:
                logger.warning(
                    f"[Instagram] Attempt {attempt + 1}/{self.max_retries} failed: {str(e)}"
                )

                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    logger.info(f"[Instagram] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

                    proxy_manager.fetch_proxies()
                else:
                    logger.error("[Instagram] All retry attempts failed")
                    raise ValueError(
                        "Instagram is blocking requests. Please try again in a few minutes."
                    )

            except Exception as e:
                logger.error(f"[Instagram] Error on attempt {attempt + 1}: {str(e)}")

                if attempt < self.max_retries - 1:
                    wait_time = (attempt + 1) * 3
                    time.sleep(wait_time)
                else:
                    # Final fallback - try alternative API
                    logger.warning(
                        "[Instagram] Standard method failed, trying alternative API..."
                    )
                    try:
                        from services.instagram_alternative_downloader import \
                            InstagramAlternativeDownloader

                        alt_downloader = InstagramAlternativeDownloader()
                        return alt_downloader.get_video_stream(url)
                    except Exception as alt_e:
                        logger.error(
                            f"[Instagram] Alternative API also failed: {str(alt_e)}"
                        )
                        raise ValueError(
                            f"Failed to download Instagram video with all methods. "
                            f"Original error: {str(e)}, Alternative error: {str(alt_e)}"
                        )

        raise ValueError("Failed to download Instagram video after all retries")

    def _download_video_with_proxy(self, video_url: str) -> BytesIO:
        """Download video with proxy support and fallback"""
        proxy = proxy_manager.get_random_proxy()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.instagram.com/",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        attempts = [
            ("proxy", proxy),
            ("direct", None),
        ]

        for attempt_type, proxy_to_use in attempts:
            try:
                logger.info(
                    f"[Instagram] Downloading video using {attempt_type} connection"
                )

                if proxy_to_use:
                    response = requests.get(
                        video_url,
                        stream=True,
                        headers=headers,
                        proxies=proxy_to_use,
                        timeout=30,
                    )
                else:
                    response = requests.get(
                        video_url, stream=True, headers=headers, timeout=30
                    )

                response.raise_for_status()

                video_data = BytesIO()
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        video_data.write(chunk)

                video_data.seek(0)
                logger.info(
                    f"[Instagram] Video downloaded successfully via {attempt_type}"
                )
                return video_data

            except Exception as e:
                logger.warning(
                    f"[Instagram] Download failed via {attempt_type}: {str(e)}"
                )
                if attempt_type == "direct":
                    raise

        raise Exception("Failed to download video with all connection methods")

    def get_video_url(self, url: str) -> tuple[str, str]:
        self._rate_limit()

        shortcode = self.extract_video_id(url)

        self._setup_session_with_proxy(self.loader.context._session)

        post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

        if not post.is_video:
            raise ValueError("This post is not a video")

        return post.video_url, shortcode
