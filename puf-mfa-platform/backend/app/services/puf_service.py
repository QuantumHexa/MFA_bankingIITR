import socket
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.database import PufDevice, User


def _hamming_hex(a: str, b: str) -> int:
    x = int(a, 16) ^ int(b, 16)
    return bin(x).count("1")


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
        ser.write(challenge.ljust(16, b"\x00")[:16])
        time.sleep(1)
        if ser.in_waiting >= 16:
            return ser.read(16).hex()
        return ""
    finally:
        ser.close()


def read_puf(challenge_hex: str, mode: str | None = None) -> str:
    mode = mode or settings.puf_bridge_mode
    if mode == "hardware":
        return read_puf_hardware(challenge_hex)
    return read_puf_virtual(challenge_hex)


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
            if expected == response:
                return True
            return _hamming_hex(expected, response) <= settings.puf_hamming_threshold

    if mask:
        # Phase 3: bit-mask fuzzy match for hardware CRPs
        pass
    if enrolled == response:
        return True
    return _hamming_hex(enrolled, response) <= settings.puf_hamming_threshold


def enroll_puf(db: Session, user: User, mode: str) -> dict:
    import secrets

    challenge = secrets.token_hex(16)
    response = read_puf(challenge, mode)
    if not response:
        return {"status": "error", "message": "PUF device did not respond"}

    device = db.query(PufDevice).filter(PufDevice.user_id == user.id).first()
    if device:
        device.enrolled_response = response
        device.challenge_seed = challenge
    else:
        device = PufDevice(user_id=user.id, enrolled_response=response, challenge_seed=challenge, device_label=f"{mode} device")
        db.add(device)

    user.puf_enabled = True
    user.puf_mode = mode
    db.commit()
    return {"status": "success", "challenge": challenge, "response_preview": response[:16] + "..."}
