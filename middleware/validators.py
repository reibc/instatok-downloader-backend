import validators as url_validators

from config import Config


def validate_video_url(url: str) -> tuple[bool, str]:
    """
    Validate video URL
    """
    if not url:
        return False, "URL is required"

    url = url.strip()

    if len(url) > 2048:
        return False, "URL is too long"

    if not url_validators.url(url):
        return False, "Invalid URL format"

    if not any(domain in url.lower() for domain in Config.ALLOWED_DOMAINS):
        return (
            False,
            f"Unsupported platform. Supported: {', '.join(Config.SUPPORTED_PLATFORMS)}",
        )

    return True, ""
