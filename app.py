import logging

from flask import Flask
from flask_cors import CORS  # Add this import
from flask_restx import Api

from config import Config
from extensions import limiter
from routes.downloads import ns as downloads_ns

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
app.config.from_object(Config)

CORS(
    app,
    resources={
        r"/*": {
            "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-API-Key"],
        }
    },
)

limiter.init_app(app)

if Config.RATE_LIMIT_ENABLED:
    limiter._default_limits = [
        f"{Config.RATE_LIMIT_PER_DAY} per day",
        f"{Config.RATE_LIMIT_PER_HOUR} per hour",
    ]

api = Api(
    app,
    version="1.0",
    title="Video Downloader API",
    description="Download videos from Instagram and TikTok",
    doc="/docs",
)

api.add_namespace(downloads_ns)

if __name__ == "__main__":
    app.run(debug=(Config.FLASK_ENV == "development"), port=5000, host="127.0.0.1")
