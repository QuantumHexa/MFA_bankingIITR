"""ESP32-C6 hardware MFA bridge — UART text protocol (MFA:ENROLL / MFA:AUTH)."""

from __future__ import annotations

import hmac
import hashlib
import os
import time
from typing import Optional

import serial

from app.config import settings
from app.services import x25519_pure as x25519

UART_TIMEOUT_S = 8.0
AUTH_TIMEOUT_S = 120.0

NONCE_HEX_LEN = 32
PUBKEY_HEX_LEN = 64
PROOF_HEX_LEN = 64

MFA_PROOF_INFO = b"esp32c6-mfa-login-proof-v1"

CMD_STATUS = "MFA:STATUS?\n"
CMD_ENROLL = "MFA:ENROLL:"
CMD_AUTH = "MFA:AUTH:"
CMD_PUBKEY = "MFA:PUBKEY?\n"

PREFIX_STATUS_OK = "MFA:STATUS:OK:"
PREFIX_ERR = "MFA:ERR:"
PREFIX_ENROLL_OK = "MFA:ENROLL:OK:"
PREFIX_PROOF_OK = "MFA:PROOF:OK:"
PREFIX_PUBKEY_OK = "MFA:PUBKEY:OK:"
PREFIX_WORK = "MFA:WORK:"

RESPONSE_PREFIXES = (
    PREFIX_STATUS_OK,
    PREFIX_ERR,
    PREFIX_ENROLL_OK,
    PREFIX_PROOF_OK,
    PREFIX_PUBKEY_OK,
)
AUTH_WAIT_PREFIXES = (PREFIX_PROOF_OK, PREFIX_ERR)


def _parse_status(line: str) -> str:
    line = line.strip()
    if line.startswith(PREFIX_STATUS_OK):
        return line[len(PREFIX_STATUS_OK) :]
    raise ValueError(f"unexpected status: {line!r}")


def _parse_enroll_response(line: str) -> tuple[str, str]:
    line = line.strip()
    if not line.startswith(PREFIX_ENROLL_OK):
        if line.startswith(PREFIX_ERR):
            raise RuntimeError(line[len(PREFIX_ERR) :])
        raise ValueError(f"unexpected enroll response: {line!r}")
    body = line[len(PREFIX_ENROLL_OK) :]
    customer_id, _, pubkey_hex = body.partition(":")
    if len(pubkey_hex) != PUBKEY_HEX_LEN:
        raise ValueError("bad pubkey length")
    return customer_id, pubkey_hex


def _parse_pubkey_response(line: str) -> str:
    line = line.strip()
    if line.startswith(PREFIX_PUBKEY_OK):
        hex_key = line[len(PREFIX_PUBKEY_OK) :]
        if len(hex_key) != PUBKEY_HEX_LEN:
            raise ValueError("bad pubkey length")
        return hex_key
    if line.startswith(PREFIX_ERR):
        raise RuntimeError(line[len(PREFIX_ERR) :])
    raise ValueError(f"unexpected pubkey response: {line!r}")


def _parse_proof_response(line: str) -> bytes:
    line = line.strip()
    if line.startswith(PREFIX_PROOF_OK):
        proof_hex = line[len(PREFIX_PROOF_OK) :]
        if len(proof_hex) != PROOF_HEX_LEN:
            raise ValueError("bad proof length")
        return bytes.fromhex(proof_hex)
    if line.startswith(PREFIX_ERR):
        raise RuntimeError(line[len(PREFIX_ERR) :])
    raise ValueError(f"unexpected proof response: {line!r}")


def _build_transcript(login_id: str, customer_id: str, nonce: bytes) -> bytes:
    return MFA_PROOF_INFO + b"|" + login_id.encode() + b"|" + customer_id.encode() + b"|" + nonce


def _compute_login_proof(shared_secret_bytes: bytes, login_id: str, customer_id: str, nonce: bytes) -> bytes:
    transcript = _build_transcript(login_id, customer_id, nonce)
    return hmac.new(shared_secret_bytes, transcript, hashlib.sha256).digest()


def _verify_login_proof(
    shared_secret_bytes: bytes,
    login_id: str,
    customer_id: str,
    nonce: bytes,
    proof: bytes,
) -> None:
    expected = _compute_login_proof(shared_secret_bytes, login_id, customer_id, nonce)
    if not hmac.compare_digest(expected, proof):
        raise ValueError("MFA device proof verification FAILED")


def _generate_ephemeral_keypair() -> tuple[int, bytes]:
    scalar = x25519.clamp_scalar(os.urandom(32))
    public = x25519.public_key_from_scalar(scalar)
    return scalar, public


def _make_nonce() -> bytes:
    return os.urandom(16)


def _open_port(port: str, baud: int) -> serial.Serial:
    ser = serial.Serial(
        port=port,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.1,
        rtscts=False,
        dsrdtr=False,
    )
    try:
        ser.setDTR(False)
        ser.setRTS(False)
    except Exception:
        pass
    time.sleep(1.0)
    ser.reset_input_buffer()
    return ser


def _send_line(ser: serial.Serial, text: str) -> None:
    ser.write(text.encode("ascii"))
    ser.flush()


def _read_line(ser: serial.Serial, timeout_s: Optional[float] = None) -> str:
    if timeout_s is None:
        timeout_s = UART_TIMEOUT_S
    deadline = time.monotonic() + timeout_s
    buf = bytearray()
    while time.monotonic() < deadline:
        chunk = ser.read(max(1, ser.in_waiting))
        if chunk:
            buf.extend(chunk)
            while b"\n" in buf:
                raw, _, buf = buf.partition(b"\n")
                line = raw.decode("ascii", errors="replace").strip()
                if line:
                    return line
        else:
            time.sleep(0.02)
    raise TimeoutError(f"no response (timeout {timeout_s:.1f}s)")


def _read_protocol_line(
    ser: serial.Serial,
    prefixes: tuple = RESPONSE_PREFIXES,
    timeout_s: Optional[float] = None,
) -> str:
    if timeout_s is None:
        timeout_s = UART_TIMEOUT_S
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            line = _read_line(ser, timeout_s=min(1.0, max(0.1, remaining)))
        except TimeoutError:
            continue
        if line.startswith(PREFIX_WORK):
            continue
        if line.startswith(prefixes):
            return line
        if line.startswith(">>>"):
            raise RuntimeError("ESP32 at REPL — deploy MFA main.py and reset.")
    raise TimeoutError(f"no MFA protocol response (timeout {timeout_s:.1f}s)")


def _wait_device_ready(
    ser: serial.Serial,
    expected: str = "mfa_enrolled",
    timeout_s: float = 20.0,
) -> str:
    deadline = time.monotonic() + timeout_s
    last_ping = 0.0

    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_ping >= 0.4:
            _send_line(ser, CMD_STATUS)
            last_ping = now

        try:
            line = _read_line(ser, timeout_s=0.5)
        except TimeoutError:
            continue

        if line.startswith(PREFIX_STATUS_OK):
            status = _parse_status(line)
            if status == expected:
                return status
            if expected == "mfa_enrolled" and status == "puf_ready":
                raise RuntimeError("device PUF is ready but MFA not enrolled — run enrollment first")
            raise RuntimeError(f"device status is {status!r}, expected {expected!r}")

        if line.startswith(">>>"):
            raise RuntimeError("ESP32 at REPL — deploy MFA main.py and reset.")

    raise TimeoutError(
        f"device not ready (no MFA:STATUS response in {timeout_s:.0f}s). "
        "Is MFA main.py running on the board?"
    )


def _default_port(port: str | None) -> str:
    return port or settings.hardware_puf_serial_port


def _default_baud(baud: int | None) -> int:
    return baud if baud is not None else settings.hardware_puf_baud


def device_status(port: str | None = None, baud: int | None = None) -> str:
    """Return device status via MFA:STATUS? (puf_not_enrolled / puf_ready / mfa_enrolled)."""
    port = _default_port(port)
    baud = _default_baud(baud)
    ser = _open_port(port, baud)
    try:
        _send_line(ser, CMD_STATUS)
        line = _read_protocol_line(ser)
        return _parse_status(line)
    finally:
        ser.close()


def enroll_device(port: str | None, customer_id: str, baud: int | None = None) -> str:
    """Enroll customer on ESP32 via MFA:ENROLL — returns device pubkey hex."""
    port = _default_port(port)
    baud = _default_baud(baud)
    ser = _open_port(port, baud)
    try:
        _send_line(ser, CMD_STATUS)
        line = _read_protocol_line(ser)
        status = _parse_status(line)
        if status == "puf_not_enrolled":
            raise RuntimeError("device PUF not enrolled — complete 30-cycle enrollment on board")
        if status not in ("puf_ready", "mfa_enrolled"):
            raise RuntimeError(f"cannot enroll: device status is {status!r}")

        _send_line(ser, CMD_ENROLL + customer_id + "\n")
        line = _read_protocol_line(ser)
        enrolled_customer, pubkey_hex = _parse_enroll_response(line)
        if enrolled_customer != customer_id:
            raise RuntimeError(f"enroll customer mismatch: {enrolled_customer!r} != {customer_id!r}")
        return pubkey_hex
    finally:
        ser.close()


def _fetch_live_device_pubkey(ser: serial.Serial) -> bytes:
    _send_line(ser, CMD_PUBKEY)
    line = _read_protocol_line(ser)
    hex_key = _parse_pubkey_response(line)
    return bytes.fromhex(hex_key)


def authenticate_device(
    port: str | None,
    login_id: str,
    customer_id: str,
    device_pubkey_hex: str,
    baud: int | None = None,
) -> dict:
    """Run MFA:AUTH flow with ephemeral X25519 + HMAC proof verification."""
    port = _default_port(port)
    baud = _default_baud(baud)
    device_pubkey = bytes.fromhex(device_pubkey_hex)

    eph_scalar, eph_public = _generate_ephemeral_keypair()
    nonce = _make_nonce()
    auth_line = f"MFA:AUTH:{login_id}:{customer_id}:{eph_public.hex()}:{nonce.hex()}"

    ser = _open_port(port, baud)
    try:
        device_status_value = _wait_device_ready(ser, expected="mfa_enrolled", timeout_s=20.0)

        live_pubkey = _fetch_live_device_pubkey(ser)
        live_hex = live_pubkey.hex()
        pubkey_match = live_hex == device_pubkey_hex.lower()

        ser.reset_input_buffer()

        t0 = time.monotonic()
        _send_line(ser, auth_line + "\n")
        line = _read_protocol_line(ser, prefixes=AUTH_WAIT_PREFIXES, timeout_s=AUTH_TIMEOUT_S)
        proof = _parse_proof_response(line)
        elapsed = time.monotonic() - t0

        shared = x25519.shared_secret(eph_scalar, device_pubkey)
        _verify_login_proof(shared, login_id, customer_id, nonce, proof)

        return {
            "verified": True,
            "device_status": device_status_value,
            "pubkey_match": pubkey_match,
            "live_pubkey_hex": live_hex,
            "stored_pubkey_hex": device_pubkey_hex.lower(),
            "elapsed_s": round(elapsed, 2),
            "login_id": login_id,
            "customer_id": customer_id,
            "proof_hex": proof.hex(),
            "mfa_nonce_hex": nonce.hex(),
        }
    finally:
        ser.close()


def hardware_device_online(port: str | None = None, baud: int | None = None) -> tuple[bool, str, str]:
    """Check if ESP32 MFA server responds. Returns (online, status, error)."""
    try:
        status = device_status(port, baud)
        return True, status, ""
    except Exception as exc:
        return False, "", str(exc)


def hardware_login_precheck(stored_pubkey_hex: str | None, port: str | None = None, baud: int | None = None) -> dict:
    """Return device status and pubkey match for hardware login step 3."""
    port = _default_port(port)
    baud = _default_baud(baud)
    ser = _open_port(port, baud)
    try:
        _send_line(ser, CMD_STATUS)
        line = _read_protocol_line(ser)
        status = _parse_status(line)

        live_pubkey_hex = None
        pubkey_match = False
        if status in ("puf_ready", "mfa_enrolled"):
            live_pubkey_hex = _fetch_live_device_pubkey(ser)
            if stored_pubkey_hex:
                pubkey_match = live_pubkey_hex.lower() == stored_pubkey_hex.lower()

        return {
            "device_status": status,
            "live_pubkey_hex": live_pubkey_hex,
            "stored_pubkey_hex": stored_pubkey_hex,
            "pubkey_match": pubkey_match,
            "ready_for_auth": status == "mfa_enrolled" and bool(stored_pubkey_hex),
        }
    finally:
        ser.close()
