"""Configuration settings."""
import os
from typing import Optional


class Settings:
    """Application settings."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////data/lis.db")
    
    # NAS Paths
    NAS_WATCH_PATH: str = os.getenv("NAS_WATCH_PATH", "/mnt/nas/lab_results")
    NAS_ARCHIVE_PATH: str = os.getenv("NAS_ARCHIVE_PATH", "/mnt/nas/archive")
    NAS_QUARANTINE_PATH: str = os.getenv("NAS_QUARANTINE_PATH", "/mnt/nas/quarantine")
    WATCH_INTERVAL: int = int(os.getenv("WATCH_INTERVAL", "30"))  # seconds
    
    # 1C API
    API_1C_URL: str = os.getenv("API_1C_URL", "https://1c.example.ru/lab/attachResult")
    API_1C_TOKEN: str = os.getenv("API_1C_TOKEN", "")
    API_1C_TIMEOUT: int = int(os.getenv("API_1C_TIMEOUT", "30"))
    API_1C_RETRY_COUNT: int = int(os.getenv("API_1C_RETRY_COUNT", "3"))
    API_1C_RETRY_DELAY: int = int(os.getenv("API_1C_RETRY_DELAY", "5"))  # seconds
    
    # SMTP
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@it-mydoc.ru")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "changeme-secret-key-for-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Admin
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "changeme")
    
    # Archive
    ARCHIVE_RETENTION_DAYS: int = int(os.getenv("ARCHIVE_RETENTION_DAYS", "90"))


settings = Settings()

