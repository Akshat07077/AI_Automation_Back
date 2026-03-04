from functools import lru_cache
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Ensure DATABASE_URL uses asyncpg driver and removes all query params.
        
        asyncpg doesn't support URL query parameters like sslmode, channel_binding, etc.
        We remove all query params and handle SSL through connect_args instead.
        """
        if isinstance(v, str):
            # Replace postgresql:// with postgresql+asyncpg://
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Also handle postgres://
            elif v.startswith("postgres://") and "+asyncpg" not in v:
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            
            # Parse URL and remove ALL query parameters
            # asyncpg doesn't support URL query params - they cause parameter conflicts
            parsed = urlparse(v)
            if parsed.query:
                # Reconstruct URL without query string
                v = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    "",  # Remove all query parameters
                    parsed.fragment
                ))
        return v

    # Google Sheets
    google_sheets_id: str = Field(..., alias="GOOGLE_SHEETS_ID")
    google_sheets_worksheet: str = Field("Leads", alias="GOOGLE_SHEETS_WORKSHEET")
    # Service account: either JSON string from env var OR file path
    google_service_account_json: str | None = Field(None, alias="GOOGLE_SERVICE_ACCOUNT_JSON")
    google_service_account_file: str | None = Field(None, alias="GOOGLE_SERVICE_ACCOUNT_FILE")

    # Gemini
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-1.5-flash", alias="GEMINI_MODEL")

    # SMTP
    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_username: str = Field(..., alias="SMTP_USERNAME")
    smtp_password: str = Field(..., alias="SMTP_PASSWORD")
    email_from: str = Field(..., alias="EMAIL_FROM")

    # IMAP
    imap_host: str = Field(..., alias="IMAP_HOST")
    imap_port: int = Field(993, alias="IMAP_PORT")
    imap_username: str = Field(..., alias="IMAP_USERNAME")
    imap_password: str = Field(..., alias="IMAP_PASSWORD")

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")

    # IMAP polling
    imap_poll_interval_seconds: int = Field(
        60, alias="IMAP_POLL_INTERVAL_SECONDS"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

