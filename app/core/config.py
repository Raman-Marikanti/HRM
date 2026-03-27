import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # A sensible default for local development if user doesn't set POSTGRES URL.
     "postgresql+psycopg://postgres:postgres@localhost:5432/hrms",
   # "postgresql+psycopg://odoo:odoo@localhost:5432/data",

)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
auth_key = os.getenv("MSG91_AUTH_KEY")
otp_template_id = os.getenv("MSG91_OTP_TEMPLATE_ID")

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "HR Management System"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "sqlite:///./hrms.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60  # 30 days
    
    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]
    
    # SMS (MSG91) - Optional for production
    MSG91_AUTH_KEY: Optional[str] = None
    MSG91_TEMPLATE_ID: Optional[str] = None
    MSG91_SENDER_ID: Optional[str] = None

    # Redis (for OTP storage)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()