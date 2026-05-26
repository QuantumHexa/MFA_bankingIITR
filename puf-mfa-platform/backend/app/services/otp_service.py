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


def send_whatsapp_otp(phone: str, otp: str) -> bool:
    """Send OTP via Twilio WhatsApp. Falls back to console log in dev."""
    message = (
        f"Your PUF-MFA Bank verification code is *{otp}*. "
        f"Valid for {settings.otp_expire_minutes} minutes. Do not share this code."
    )

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("[DEV OTP] Phone +91%s -> %s", phone, otp)
        print(f"\n[WHATSAPP OTP DEV] +91{phone}: {otp}\n")
        return False

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            from_=settings.twilio_whatsapp_from,
            body=message,
            to=f"whatsapp:+91{phone}",
        )
        return True
    except Exception as exc:
        logger.error("WhatsApp OTP failed: %s", exc)
        print(f"\n[WHATSAPP OTP FALLBACK] +91{phone}: {otp}\n")
        return False
