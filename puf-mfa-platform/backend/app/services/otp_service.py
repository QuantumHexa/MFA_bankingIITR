import logging
import secrets
import smtplib
import socket
import ssl
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
    # Keep wording plain — "Bank"/promo-like phrasing from a free Gmail often hits spam filters
    subject = "Your SecureVault login code"
    text_body = (
        f"SecureVault login code: {otp}\n\n"
        f"This code expires in {settings.otp_expire_minutes} minutes.\n"
        f"Do not share it with anyone.\n\n"
        f"If you did not try to sign in, you can ignore this message.\n"
    )
    # Plain text only is usually less likely to be flagged than heavy HTML
    html_body = (
        f"<p>SecureVault login code: <strong>{otp}</strong></p>"
        f"<p>This code expires in {settings.otp_expire_minutes} minutes. Do not share it.</p>"
        f"<p>If you did not try to sign in, ignore this message.</p>"
    )
    return subject, text_body, html_body


def _smtp_configured() -> bool:
    return bool(settings.smtp_username and settings.smtp_password)


def _create_ipv4_connection(host: str, port: int, timeout: float) -> socket.socket:
    """Connect over IPv4 only. Docker/cloud VMs often have IPv6 with no route (errno 101)."""
    last_err: OSError | None = None
    for family, socktype, proto, _, sockaddr in socket.getaddrinfo(
        host, port, socket.AF_INET, socket.SOCK_STREAM
    ):
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_err = exc
            sock.close()
    if last_err:
        raise last_err
    raise OSError(f"No IPv4 address for {host}:{port}")


class _IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        return _create_ipv4_connection(host, port, timeout)


class _IPv4SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        sock = _create_ipv4_connection(host, port, timeout)
        context = self.context or ssl.create_default_context()
        return context.wrap_socket(sock, server_hostname=self._host)


def _smtp_unreachable_hint(exc: BaseException) -> str:
    err = str(exc)
    if "101" in err or "unreachable" in err.lower() or "timed out" in err.lower() or "111" in err:
        return (
            f"{exc}. The server cannot reach {settings.smtp_host}:{settings.smtp_port}. "
            "Render free web services block outbound SMTP (ports 25/465/587), so Gmail SMTP "
            "cannot work there. Set SENDGRID_API_KEY + OTP_EMAIL_FROM to send OTP over HTTPS:443, "
            "or upgrade the Render service to a paid instance."
        )
    return err


def _send_via_gmail_smtp(to_email: str, otp: str) -> None:
    subject, text_body, html_body = _otp_email_bodies(otp)
    # From must match the authenticated Gmail account or providers flag spoofing
    from_email = (settings.otp_email_from or settings.smtp_username).strip()
    if from_email.lower() != settings.smtp_username.strip().lower():
        logger.warning(
            "OTP_EMAIL_FROM (%s) differs from SMTP_USERNAME (%s); using SMTP_USERNAME to reduce spam risk",
            from_email,
            settings.smtp_username,
        )
        from_email = settings.smtp_username.strip()
    from_name = settings.otp_email_from_name or "SecureVault"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = from_email
    msg["X-Priority"] = "1"
    msg["X-Auto-Response-Suppress"] = "All"
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    ports: list[int] = [settings.smtp_port]
    if 587 not in ports:
        ports.append(587)
    if 465 not in ports:
        ports.append(465)

    last_err: BaseException | None = None
    for port in ports:
        try:
            if port == 465:
                client: smtplib.SMTP = _IPv4SMTP_SSL(settings.smtp_host, port, timeout=20)
            else:
                client = _IPv4SMTP(settings.smtp_host, port, timeout=20)
            with client as server:
                if port != 465:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            logger.info(
                "Email OTP sent via SMTP %s:%s to %s",
                settings.smtp_host,
                port,
                mask_email(to_email),
            )
            return
        except Exception as exc:
            last_err = exc
            logger.warning("SMTP %s:%s failed: %s", settings.smtp_host, port, exc)

    assert last_err is not None
    raise last_err


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
    """Send OTP via HTTPS mail API when set (Render-safe), else Gmail SMTP."""
    subject, text_body, _ = _otp_email_bodies(otp)

    # HTTPS first: Render free blocks SMTP 25/465/587 (errno 101).
    if settings.sendgrid_api_key and settings.otp_email_from:
        try:
            _send_via_sendgrid(email, otp)
            return
        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("SendGrid email OTP failed: %s", exc)
            raise RuntimeError(f"Email OTP delivery failed: {exc}") from exc

    if _smtp_configured():
        try:
            _send_via_gmail_smtp(email, otp)
            return
        except Exception as exc:
            logger.error("SMTP email OTP failed: %s", exc)
            raise RuntimeError(f"Email OTP delivery failed: {_smtp_unreachable_hint(exc)}") from exc

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
