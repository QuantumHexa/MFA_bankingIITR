from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite:///./puf_mfa.db"

    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

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

    admin_email: str = "admin@pufbank.dev"
    admin_password: str = "change-admin-password"


settings = Settings()
