# Reels Downloader - Backend API

Backend API for downloading videos from Instagram and TikTok.

## Tech Stack
- Python 3.11
- Flask
- Flask-RESTX
- Instaloader

## Quick Start

### Local Development
```bash
pip install -r requirements.txt

python app.py
```

### Docker
```bash
docker-compose up --build
http://localhost:5000/docs
```

## API Endpoints

- `POST /download` - Download video
- `GET /platforms` - Get supported platforms
- `GET /health` - Health check
- `GET /docs` - API documentation

## Environment Variables

Copy `.env.example` to `.env` and configure:
```env
FLASK_ENV=production
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=5
MAX_DOWNLOAD_SIZE_MB=500
ALLOWED_DOMAINS=instagram.com,tiktok.com
API_KEY_REQUIRED=false
```

### Docker
```bash
docker-compose up -d --build
```
