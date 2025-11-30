import logging
from abc import ABC, abstractmethod
from io import BytesIO

logger = logging.getLogger(__name__)


class BaseDownloader(ABC):
    """Abstract base class for video downloaders"""

    @abstractmethod
    def get_video_stream(self, url: str) -> tuple[BytesIO, str, str]:
        """
        Download video and return stream
        """
        pass

    @abstractmethod
    def get_video_url(self, url: str) -> tuple[str, str]:
        """
        Get direct video URL without downloading
        """
        pass

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is from this platform
        """
        pass

    @abstractmethod
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from URL
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return platform name"""
        pass
