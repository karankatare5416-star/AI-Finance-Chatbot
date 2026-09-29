import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


class Config:
    _secret_key = os.getenv("SECRET_KEY")
    _environment = os.getenv("FLASK_ENV", "production").lower()
    _preview_mode = os.getenv("MANUS_PREVIEW", "false").lower() in {"1", "true", "yes"}
    if _environment == "production" and not _secret_key:
        raise RuntimeError("SECRET_KEY must be configured in production")
    SECRET_KEY = _secret_key or "dev-only-change-me"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'personal_finance.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None" if _environment == "production" or _preview_mode else "Lax"
    SESSION_COOKIE_SECURE = _environment == "production" or _preview_mode
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")
    USE_NGROK = os.getenv("USE_NGROK", "false").lower() in {"1", "true", "yes"}
    DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@financebot.com")
    DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DemoFinance123!")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
