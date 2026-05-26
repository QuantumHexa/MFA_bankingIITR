import hashlib
import hmac
import socket
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.database import PufDevice, User

ENROLL_SAMPLES = 5


def _hamming_hex(a: str, b: str) -> int:
    width = max(len(a), len(b))
    x = int(a.ljust(width, "0"), 16) ^ int(b.ljust(width, "0"), 16)
    return bin(x).count("1")


def _hamming_masked(response: str, reference: str, mask: str | None) -> int:
    if not mask:
        return _hamming_hex(response, reference)
    width = max(len(response), len(reference), len(mask))
    diff = int(response.ljust(width, "0"), 16) ^ int(reference.ljust(width, "0"), 16)
    mask_int = int(mask.ljust(width, "f"), 16)
    return bin(diff & mask_int).count("1")


def read_puf_virtual(challenge_hex: str) -> str:
    challenge = bytes.fromhex(challenge_hex.ljust(32, "0")[:32])
    sock = socket.create_connection((settings.virtual_puf_host, settings.virtual_puf_port), timeout=5)
    try:
        sock.sendall(challenge.ljust(16, b"\x00")[:16])
        time.sleep(0.05)
        data = b""
        while len(data) < 16:
            chunk = sock.recv(16 - len(data))
            if not chunk:
                break
            data += chunk
        return data.hex()
    finally:
        sock.close()


def read_puf_hardware(challenge_hex: str) -> str:
    import serial

    challenge = bytes.fromhex(challenge_hex.ljust(32, "0")[:32])
    ser = serial.Serial(settings.hardware_puf_serial_port, settings.hardware_puf_baud, timeout=2)
    try:
        ser.reset_input_buffer()
        ser.write(challenge.ljust(16, b"\x00")[:16])
        time.sleep(0.8)
        data = b""
        deadline = time.time() + 2
        while len(data) < 16 and time.time() < deadline:
            waiting = ser.in_waiting
            if waiting:
                data += ser.read(min(waiting, 16 - len(data)))
            else:
                time.sleep(0.05)
        return data.hex() if len(data) >= 16 else ""
    finally:
        ser.close()


def read_puf(challenge_hex: str, mode: str | None = None) -> str:
    mode = mode or settings.puf_bridge_mode
    if mode == "hardware":
        return read_puf_hardware(challenge_hex)
    return read_puf_virtual(challenge_hex)


def _build_reference_and_mask(reads: list[str]) -> tuple[str, str]:
    """Majority-vote reference + per-bit reliability mask (stable bits only)."""
    valid = [r for r in reads if r and len(r) >= 32]
    if not valid:
        return "", ""

    byte_len = len(valid[0]) // 2
    ref = bytearray(byte_len)
    mask = bytearray(byte_len)

    for i in range(byte_len):
        for bit in range(8):
            values = []
            for resp in valid:
                values.append((bytes.fromhex(resp)[i] >> (7 - bit)) & 1)
            if len(set(values)) == 1:
                mask[i] |= 1 << (7 - bit)
                if values[0]:
                    ref[i] |= 1 << (7 - bit)
    return ref.hex(), mask.hex()


def verify_puf_response(
    challenge: str,
    response: str,
    enrolled: str,
    mask: str | None = None,
    mode: str = "virtual",
) -> bool:
    if mode == "virtual":
        expected = read_puf(challenge, mode)
        if expected:
            return _hamming_hex(expected, response) <= settings.puf_hamming_threshold

    distance = _hamming_masked(response, enrolled, mask)
    return distance <= settings.puf_hamming_threshold


def derive_session_key(challenge: str, response: str, nonce: str) -> str:
    """Lightweight session key from verified PUF material (SHA-256/HMAC)."""
    material = f"{challenge}:{response}:{nonce}".encode()
    return hmac.new(settings.secret_key.encode(), material, hashlib.sha256).hexdigest()


def enroll_puf(db: Session, user: User, mode: str) -> dict:
    import secrets

    challenge = secrets.token_hex(16)
    samples = ENROLL_SAMPLES if mode == "hardware" else 1
    reads = [read_puf(challenge, mode) for _ in range(samples)]
    reads = [r for r in reads if r]

    if not reads:
        return {"status": "error", "message": f"PUF device did not respond ({mode} mode)"}

    if mode == "hardware" and len(reads) >= 2:
        enrolled, reliability_mask = _build_reference_and_mask(reads)
    else:
        enrolled = reads[0]
        reliability_mask = None

    device = db.query(PufDevice).filter(PufDevice.user_id == user.id).first()
    label = "CMOD A7 Arbiter PUF" if mode == "hardware" else "Virtual PUF Device"
    if device:
        device.enrolled_response = enrolled
        device.reliability_mask = reliability_mask
        device.challenge_seed = challenge
        device.device_label = label
    else:
        device = PufDevice(
            user_id=user.id,
            enrolled_response=enrolled,
            reliability_mask=reliability_mask,
            challenge_seed=challenge,
            device_label=label,
        )
        db.add(device)

    user.puf_enabled = True
    user.puf_mode = mode
    db.commit()
    return {
        "status": "success",
        "mode": mode,
        "challenge": challenge,
        "response_preview": enrolled[:16] + "...",
        "has_reliability_mask": bool(reliability_mask),
        "samples_used": len(reads),
    }
