import logging
import secrets
import smtplib
import string
from email.message import EmailMessage

import httpx

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


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        masked_local = (local[:1] or "*") + "***"
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


def _otp_email_bodies(otp: str) -> tuple[str, str, str]:
    subject = "SecureVault verification code"
    text_body = (
        f"Your SecureVault Bank verification code is {otp}.\n\n"
        f"Valid for {settings.otp_expire_minutes} minutes. Do not share this code.\n"
        f"If you did not request this, you can ignore this email."
    )
    html_body = (
        f"<p>Your SecureVault Bank verification code is "
        f"<strong style=\"font-size:18px;letter-spacing:2px\">{otp}</strong>.</p>"
        f"<p>Valid for {settings.otp_expire_minutes} minutes. Do not share this code.</p>"
        f"<p style=\"color:#666;font-size:12px\">If you did not request this, you can ignore this email.</p>"
    )
    return subject, text_body, html_body


def _smtp_configured() -> bool:
    return bool(settings.smtp_username and settings.smtp_password)


def _send_via_gmail_smtp(to_email: str, otp: str) -> None:
    subject, text_body, html_body = _otp_email_bodies(otp)
    from_email = settings.otp_email_from or settings.smtp_username
    from_name = settings.otp_email_from_name or "SecureVault"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)

    logger.info("Email OTP sent via SMTP to %s", mask_email(to_email))


def _send_via_sendgrid(to_email: str, otp: str) -> None:
    subject, text_body, html_body = _otp_email_bodies(otp)
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {
            "email": settings.otp_email_from,
            "name": settings.otp_email_from_name or "SecureVault",
        },
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }
    response = httpx.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15.0,
    )
    if response.status_code >= 400:
        detail = response.text[:300]
        raise RuntimeError(f"Email OTP delivery failed: {response.status_code} {detail}")
    logger.info("Email OTP sent via SendGrid to %s", mask_email(to_email))


def send_email_otp(email: str, otp: str) -> None:
    """Send OTP via Gmail SMTP (preferred) or SendGrid. Falls back to console mock."""
    subject, text_body, _ = _otp_email_bodies(otp)

    if _smtp_configured():
        try:
            _send_via_gmail_smtp(email, otp)
            return
        except Exception as exc:
            logger.error("SMTP email OTP failed: %s", exc)
            raise RuntimeError(f"Email OTP delivery failed: {exc}") from exc

    if settings.sendgrid_api_key and settings.otp_email_from:
        try:
            _send_via_sendgrid(email, otp)
            return
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("SendGrid email OTP failed: %s", exc)
            raise RuntimeError(f"Email OTP delivery failed: {exc}") from exc

    print(
        f"\n========================================\n"
        f"[MOCK EMAIL OTP] To: {email}\n"
        f"Subject: {subject}\n"
        f"{text_body}\n"
        f"========================================\n",
        flush=True,
    )
    logger.warning("Email SMTP not configured. Mock email OTP [%s] logged to console.", otp)


def send_whatsapp_otp(phone: str, otp: str) -> None:
    """Legacy WhatsApp OTP via Twilio. Kept for optional future use."""
    message = (
        f"Your SecureVault Bank verification code is *{otp}*. "
        f"Valid for {settings.otp_expire_minutes} minutes. Do not share this code."
    )

    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        print(
            f"\n========================================\n"
            f"[MOCK OTP DELIVERY] Phone: {phone}\n"
            f"{message}\n"
            f"========================================\n",
            flush=True,
        )
        logger.warning("Twilio not configured. Mock OTP [%s] logged to console.", otp)
        return

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
