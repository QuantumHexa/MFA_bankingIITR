from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-in-production"
    password_pepper: str = ""
    database_url: str = "sqlite:///./puf_mfa.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    hsts_max_age: int = 31536000
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' https: wss:; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    trusted_proxy_headers: bool = False

    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_refresh_rotate_days: int = 14
    access_cookie_name: str = "sv_access_token"
    refresh_cookie_name: str = "sv_refresh_token"
    cookie_domain: str = ""
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    access_cookie_max_age_minutes: int = 30
    refresh_cookie_max_age_days: int = 14

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    otp_expire_minutes: int = 5

    puf_bridge_mode: str = "virtual"
    virtual_puf_host: str = "127.0.0.1"
    virtual_puf_port: int = 8765
    hardware_puf_serial_port: str = "COM3"
    hardware_puf_baud: int = 115200
    puf_hamming_threshold: int = 5
    rsa_private_key_path: str = "server_rsa_private.pem"

    admin_email: str = "admin@pufbank.dev"
    admin_password: str = "admin"

    otp_max_attempts: int = 5
    otp_lock_minutes: int = 10
    otp_resend_cooldown_seconds: int = 30
    otp_max_sends_per_session: int = 3

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}


def validate_security_settings(settings: Settings) -> None:
    if settings.is_production:
        if settings.secret_key == "dev-secret-change-in-production" or len(settings.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be set to a strong value in production.")
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            import logging
            logging.getLogger("app.config").warning(
                "Twilio credentials not configured in production. WhatsApp OTPs will be printed to console log instead."
            )
        if settings.admin_password == "change-admin-password":
            raise RuntimeError("ADMIN_PASSWORD must be changed in production.")
        if not settings.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true in production.")
        if not all(origin.startswith("https://") for origin in settings.cors_origin_list):
            raise RuntimeError("All CORS_ORIGINS must be HTTPS in production.")


settings = Settings()
