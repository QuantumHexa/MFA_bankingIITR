"""
ESP32-C6 serial PUF server for SecureVault MFA.

Protocol (must match backend read_puf_hardware):
  - Host sends exactly 16 bytes (challenge)
  - Device replies with exactly 16 bytes (HMAC-SHA256 response)

Prerequisites (from ESP32C6_PUF_Key_Generation.pdf):
  1. Flash MicroPython v1.28+ for ESP32-C6
  2. Upload PDF project files (boot.py, main.py, sketch.py, hkdf.py, ...)
  3. Complete 30-cycle enrollment (.puf_enrolled + puf_helper.json on flash)

Then upload THIS file and run it instead of the encrypt/decrypt demo loop,
OR import run_serial_server() from your main.py after enrollment.

Usage on board (Thonny REPL):
  >>> import puf_serial_server
  >>> puf_serial_server.run_serial_server()
"""

try:
    import uhashlib as hashlib
    import ubinascii
except ImportError:
    import hashlib
    import binascii as ubinascii

import sys

RESPONSE_LEN = 16
CHALLENGE_LEN = 16


def _hmac_sha256(key: bytes, msg: bytes) -> bytes:
    block = 64
    if len(key) > block:
        key = hashlib.sha256(key).digest()
    key = key + b"\x00" * (block - len(key))
    o_pad = bytes((x ^ 0x5C) for x in key)
    i_pad = bytes((x ^ 0x36) for x in key)
    return hashlib.sha256(o_pad + hashlib.sha256(i_pad + msg).digest()).digest()


def _derive_key_from_real_puf() -> bytes:
    """Use enrolled ESP32-C6 PUF reconstruction (PDF project modules)."""
    import os

    if ".puf_enrolled" not in os.listdir("/"):
        raise RuntimeError("Board not enrolled. Run 30-cycle enrollment from the PDF guide first.")

    # main.py in the PDF project exposes reconstruction logic used at boot.
    import main  # noqa: F401 — side effect: may reconstruct on import

    if hasattr(main, "get_aes_key_bytes"):
        key = main.get_aes_key_bytes()
        if key and len(key) >= 16:
            return bytes(key[:16])

    if hasattr(main, "reconstruct"):
        ok = main.reconstruct()
        if not ok:
            raise RuntimeError("PUF reconstruction failed on device")
        if hasattr(main, "AES_KEY") and main.AES_KEY:
            return bytes(main.AES_KEY[:16])

    raise RuntimeError(
        "Could not read AES key from main.py. "
        "Add get_aes_key_bytes() to main.py that returns the reconstructed 16-byte key."
    )


def _derive_key_fallback_test_only() -> bytes:
    """Fallback for wiring tests only — NOT secure for production."""
    import machine

    uid = machine.unique_id()
    return hashlib.sha256(uid).digest()[:16]


def get_device_key(use_real_puf: bool = True) -> bytes:
    if use_real_puf:
        try:
            return _derive_key_from_real_puf()
        except Exception as exc:
            print("WARN: real PUF key unavailable:", exc)
            print("WARN: using unique_id fallback — enrollment demo only")
    return _derive_key_fallback_test_only()


def compute_response(challenge: bytes, key: bytes) -> bytes:
    challenge = (challenge + b"\x00" * CHALLENGE_LEN)[:CHALLENGE_LEN]
    return _hmac_sha256(key, challenge)[:RESPONSE_LEN]


def _read_exact_uart(uart, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = uart.read(n - len(buf))
        if chunk:
            buf += chunk
    return buf


def _read_exact_stdin(n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sys.stdin.buffer.read(n - len(buf))
        if chunk:
            buf += chunk
    return buf


def run_serial_server(use_real_puf: bool = True, baud: int = 115200) -> None:
    """Listen for 16-byte challenges and reply with 16-byte HMAC responses."""
    uart = None
    try:
        from machine import UART

        uart = UART(0, baudrate=baud, timeout=5000)
    except Exception:
        uart = None

    key = get_device_key(use_real_puf=use_real_puf)
    print("PUF serial server ready")
    print("Key prefix:", ubinascii.hexlify(key[:4]).decode())
    print("Waiting for 16-byte challenges...")

    while True:
        if uart is not None:
            challenge = _read_exact_uart(uart, CHALLENGE_LEN)
            response = compute_response(challenge, key)
            uart.write(response)
        else:
            challenge = _read_exact_stdin(CHALLENGE_LEN)
            response = compute_response(challenge, key)
            sys.stdout.buffer.write(response)
            sys.stdout.buffer.flush()

        try:
            print("C=", ubinascii.hexlify(challenge).decode(), "R=", ubinascii.hexlify(response).decode())
        except Exception:
            pass


if __name__ == "__main__":
    run_serial_server(use_real_puf=True)
