import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 5))
    RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", 50))
    RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", 200))

    MAX_DOWNLOAD_SIZE_MB = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", 500))
    ALLOWED_DOMAINS = os.getenv(
        "ALLOWED_DOMAINS", "instagram.com,www.instagram.com,tiktok.com,www.tiktok.com"
    ).split(",")
    API_KEY_REQUIRED = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
    API_KEY = os.getenv("API_KEY", "")

    # Platforms
    SUPPORTED_PLATFORMS = os.getenv("SUPPORTED_PLATFORMS", "instagram,tiktok").split(
        ","
    )

    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
