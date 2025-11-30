import hashlib
import hmac
import logging
from functools import wraps
from urllib.parse import urlparse

import bleach
import validators
from flask import request

from config import Config

logger = logging.getLogger(__name__)


def sanitize_input(data: dict) -> dict:
    """
    sanitize input data
    """
    if not data:
        return {}

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            value = value.replace("\x00", "")

            value = bleach.clean(value, tags=[], strip=True)
            value = value[:2048]

        sanitized[key] = value

    return sanitized


def require_api_key(f):
    """decorator to require API key if enabled"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not Config.API_KEY_REQUIRED:
            return f(*args, **kwargs)

        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return {"error": "API key required"}, 401

        if not secrets_compare(api_key, Config.API_KEY):
            return {"error": "Invalid API key"}, 403

        return f(*args, **kwargs)

    return decorated_function


def secrets_compare(a: str, b: str) -> bool:
    """
    constant-time string comparison to prevent timing attacks
    """
    return hmac.compare_digest(a, b)


def validate_content_type(f):
    """decorator to validate Content-Type header"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                return {"error": "Content-Type must be application/json"}, 415
        return f(*args, **kwargs)

    return decorated_function


def rate_limit_key():
    """
    generate rate limit key based on IP and API key
    """

    api_key = request.headers.get("X-API-Key", "anonymous")
    ip = request.remote_addr or "unknown"

    key = f"{ip}:{api_key}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
