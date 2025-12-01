import logging

from flask import request, send_file
from flask_restx import Namespace, Resource, fields
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import limiter
from middleware.security import (require_api_key, sanitize_input,
                                 validate_content_type)
from middleware.validators import validate_video_url
from services.downloader_factory import DownloaderFactory

logger = logging.getLogger(__name__)

ns = Namespace("", description="Video download operations for multiple platforms")

download_model = ns.model(
    "DownloadRequest",
    {
        "url": fields.String(
            required=True,
            description="Video URL (Instagram, TikTok)",
            example="https://www.instagram.com/reel/C1234567890/",
        )
    },
)


@ns.route("/download")
class VideoDownload(Resource):
    @ns.doc("download_video", security="apikey" if Config.API_KEY_REQUIRED else None)
    @ns.expect(download_model)
    @ns.response(200, "Success - Returns video file")
    @ns.response(400, "Invalid URL or request")
    @ns.response(401, "API key required")
    @ns.response(403, "Invalid API key")
    @ns.response(404, "Video not found")
    @ns.response(429, "Rate limit exceeded")
    @ns.response(500, "Download failed")
    @limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE} per minute")
    @require_api_key
    @validate_content_type
    def post(self):
        """Download video from Instagram, TikTok"""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400

            data = sanitize_input(data)
            video_url = data.get("url", "").strip()

            is_valid, error_message = validate_video_url(video_url)
            if not is_valid:
                logger.warning(f"Invalid URL: {video_url} - {error_message}")
                return {"error": error_message}, 400

            logger.info(f"Download request for: {video_url} from {request.remote_addr}")

            try:
                downloader = DownloaderFactory.get_downloader(video_url)
            except ValueError as e:
                logger.warning(f"Unsupported platform: {str(e)}")
                return {"error": str(e)}, 400

            video_stream, video_id, filename = downloader.get_video_stream(video_url)

            file_size_mb = len(video_stream.getvalue()) / (1024 * 1024)
            if file_size_mb > Config.MAX_DOWNLOAD_SIZE_MB:
                logger.error(f"File too large: {file_size_mb}MB")
                return {
                    "error": f"File size ({file_size_mb:.1f}MB) exceeds limit ({Config.MAX_DOWNLOAD_SIZE_MB}MB)"
                }, 400

            logger.info(f"Successfully streaming: {filename} ({file_size_mb:.1f}MB)")

            return send_file(
                video_stream,
                as_attachment=True,
                download_name=filename,
                mimetype="video/mp4",
            )

        except ValueError as e:
            logger.error(f"ValueError: {str(e)}")
            return {"error": str(e)}, 404
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return {"error": "An unexpected error occurred"}, 500


@ns.route("/platforms")
class SupportedPlatforms(Resource):
    @ns.doc("get_platforms")
    @ns.response(200, "Success - Returns supported platforms")
    def get(self):
        """Get list of supported platforms"""
        platforms = DownloaderFactory.get_supported_platforms()
        return {
            "supported_platforms": platforms,
            "examples": {
                "instagram": "https://www.instagram.com/reel/xxx/",
                "tiktok": "https://www.tiktok.com/@user/video/xxx",
            },
        }, 200


@ns.route("/info")
class VideoInfo(Resource):
    @ns.doc("get_video_info")
    @ns.expect(download_model)
    @ns.response(200, "Success - Returns video information")
    @ns.response(400, "Invalid URL")
    @ns.response(404, "Video not found")
    @limiter.limit(f"{Config.RATE_LIMIT_PER_MINUTE} per minute")
    def post(self):
        """Get video information without downloading"""
        try:
            data = request.get_json()
            if not data:
                return {"error": "No data provided"}, 400

            data = sanitize_input(data)
            video_url = data.get("url", "").strip()

            is_valid, error_message = validate_video_url(video_url)
            if not is_valid:
                return {"error": error_message}, 400

            downloader = DownloaderFactory.get_downloader(video_url)
            direct_url, video_id = downloader.get_video_url(video_url)

            return {
                "platform": downloader.platform_name,
                "video_id": video_id,
                "direct_url": direct_url,
                "note": "Use /download endpoint to download this video",
            }, 200

        except ValueError as e:
            return {"error": str(e)}, 400
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {"error": "Failed to get video info"}, 404


@ns.route("/health")
class HealthCheck(Resource):
    @ns.doc("health_check")
    @ns.response(200, "Service is healthy")
    def get(self):
        """Check if the service is running"""
        return {
            "status": "healthy",
            "supported_platforms": Config.SUPPORTED_PLATFORMS,
            "rate_limit_enabled": Config.RATE_LIMIT_ENABLED,
        }, 200
