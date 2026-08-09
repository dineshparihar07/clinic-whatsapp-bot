import os
from pydantic_settings import BaseSettings
from pydantic import Field
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # WhatsApp Configuration
    whatsapp_token: str = Field(default="", description="WhatsApp Business Token")
    whatsapp_phone_number_id: str = Field(default="", description="WhatsApp Phone Number ID")
    whatsapp_verify_token: str = Field(default="", description="Webhook Verify Token")

    # Gemini Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")

    # Database Configuration
    database_url: str = Field(default="", description="PostgreSQL Connection URL")

    # Security
    cron_secret: str = Field(default="your_cron_secret", description="Secret token for cron jobs")

    # Server Configuration
    port: int = Field(default=3000, description="Server port")
    env: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=False, description="Debug mode")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def is_configured(self) -> bool:
        """Check if all required settings are configured"""
        required = [
            self.whatsapp_token,
            self.whatsapp_phone_number_id,
            self.gemini_api_key,
            self.database_url
        ]
        return all(required)

    def get_missing_settings(self) -> list:
        """Get list of missing required settings"""
        missing = []
        if not self.whatsapp_token:
            missing.append("WHATSAPP_TOKEN")
        if not self.whatsapp_phone_number_id:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.database_url:
            missing.append("DATABASE_URL")
        return missing

# Load settings
settings = Settings()

# Log configuration status
if settings.is_configured():
    logger.info("✅ All required settings configured")
else:
    missing = settings.get_missing_settings()
    logger.warning(f"⚠️  Missing settings: {', '.join(missing)}")
