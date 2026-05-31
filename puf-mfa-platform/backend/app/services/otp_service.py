import logging
import secrets
import string

from app.config import settings
from app.services.auth_service import hash_password, verify_password

logger = logging.getLogger(__name__)


def generate_otp(length: int = 6) -> str:
    alphabet = string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def verify_otp(plain: str, hashed: str) -> bool:
    return verify_password(plain, hashed)


def hash_otp(otp: str) -> str:
    return hash_password(otp)


def send_whatsapp_otp(phone: str, otp: str) -> None:
    """Send OTP via Twilio WhatsApp. Raises if Twilio is not configured or send fails."""
    message = (
        f"Your SecureVault Bank verification code is *{otp}*. "
        f"Valid for {settings.otp_expire_minutes} minutes. Do not share this code."
    )

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        raise RuntimeError(
            "Twilio WhatsApp is not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in backend/.env"
        )

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            from_=settings.twilio_whatsapp_from,
            body=message,
            to=f"whatsapp:+91{phone}",
        )
        logger.info("WhatsApp OTP sent to +91%s", phone)
    except Exception as exc:
        logger.error("WhatsApp OTP failed: %s", exc)
        raise RuntimeError(f"WhatsApp OTP delivery failed: {exc}") from exc
