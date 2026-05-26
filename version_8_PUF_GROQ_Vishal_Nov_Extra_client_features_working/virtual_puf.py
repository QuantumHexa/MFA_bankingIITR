#!/usr/bin/env python3
"""
Virtual Arduino PUF Device (Python)

Simulates a hardware PUF that responds to a 128-bit challenge with a
deterministic 128-bit (16-byte) response. Same device + same challenge
always yields the same response (PUF-like behavior).

Usage:
  TCP mode (recommended, no COM port needed):
    python virtual_puf.py --mode tcp --port 8765

  Serial mode (requires virtual COM pair, e.g. com0com):
    python virtual_puf.py --mode serial --port COM3
"""

import argparse
import hashlib
import hmac
import socket
import sys
import threading
import time

try:
    import serial
except ImportError:
    serial = None

# 128-bit challenge used by the banking client (matches Arduino firmware)
DEFAULT_CHALLENGE = bytes.fromhex("ffc3330ff0aacc30ff0aacc01ffc3301")
RESPONSE_BITS = 128
RESPONSE_BYTES = RESPONSE_BITS // 8  # 16 bytes

DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 8765
DEFAULT_BAUD = 115200


class VirtualPUF:
    """Generates deterministic 128-bit PUF responses from 128-bit challenges."""

    def __init__(self, device_id: str = "virtual-arduino-puf-001"):
        self.device_id = device_id
        self._secret = hashlib.sha256(device_id.encode("utf-8")).digest()

    @property
    def device_id(self) -> str:
        return self._device_id

    @device_id.setter
    def device_id(self, value: str):
        self._device_id = value
        self._secret = hashlib.sha256(value.encode("utf-8")).digest()

    def generate_response(self, challenge: bytes) -> bytes:
        """Return exactly 128 bits (16 bytes) for the given challenge."""
        if len(challenge) < RESPONSE_BYTES:
            challenge = challenge.ljust(RESPONSE_BYTES, b"\x00")
        else:
            challenge = challenge[:RESPONSE_BYTES]
        return hmac.new(self._secret, challenge, hashlib.sha256).digest()[:RESPONSE_BYTES]

    def generate_response_hex(self, challenge: bytes | None = None) -> str:
        challenge = challenge if challenge is not None else DEFAULT_CHALLENGE
        return self.generate_response(challenge).hex()

    def handle_exchange(self, challenge: bytes) -> bytes:
        """Process one challenge/response exchange."""
        return self.generate_response(challenge)


class VirtualPUFClient:
    """Banking-client helper: talk to virtual_puf.py over TCP."""

    def __init__(self, host: str = DEFAULT_TCP_HOST, port: int = DEFAULT_TCP_PORT):
        self.host = host
        self.port = port
        self._sock = None

    @property
    def connected(self) -> bool:
        return self._sock is not None

    def connect(self) -> None:
        self.close()
        self._sock = socket.create_connection((self.host, self.port), timeout=5)

    def read_puf(
        self, challenge: bytes | None = None, delay: float = 0.05
    ) -> str:
        if not self._sock:
            raise RuntimeError("Not connected to virtual PUF")
        challenge = challenge if challenge is not None else DEFAULT_CHALLENGE
        self._sock.sendall(challenge)
        time.sleep(delay)
        data = b""
        while len(data) < RESPONSE_BYTES:
            chunk = self._sock.recv(RESPONSE_BYTES - len(data))
            if not chunk:
                raise RuntimeError("Virtual PUF closed connection")
            data += chunk
        return data.hex()

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


def _log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _handle_tcp_client(puf: VirtualPUF, conn: socket.socket, addr) -> None:
    try:
        conn.settimeout(30)
        while True:
            challenge = b""
            while len(challenge) < RESPONSE_BYTES:
                chunk = conn.recv(RESPONSE_BYTES - len(challenge))
                if not chunk:
                    return
                challenge += chunk
            response = puf.handle_exchange(challenge)
            conn.sendall(response)
            _log(
                f"TCP {addr}: challenge={challenge.hex()[:32]}... "
                f"-> response={response.hex()}"
            )
    except (ConnectionResetError, BrokenPipeError, TimeoutError, OSError):
        pass
    finally:
        conn.close()


def run_tcp_server(
    puf: VirtualPUF, host: str = DEFAULT_TCP_HOST, port: int = DEFAULT_TCP_PORT
) -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    _log(f"Virtual PUF (TCP) listening on {host}:{port}")
    _log(f"Device ID: {puf.device_id}")
    _log(f"Test response: {puf.generate_response_hex()}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=_handle_tcp_client, args=(puf, conn, addr), daemon=True
            )
            thread.start()
    except KeyboardInterrupt:
        _log("Stopping TCP server...")
    finally:
        server.close()


def run_serial_server(puf: VirtualPUF, port: str, baud: int = DEFAULT_BAUD) -> None:
    if serial is None:
        raise RuntimeError("pyserial is required for serial mode: pip install pyserial")

    ser = serial.Serial(port, baud, timeout=1)
    _log(f"Virtual PUF (Serial) on {port} @ {baud} baud")
    _log(f"Device ID: {puf.device_id}")
    _log(f"Test response: {puf.generate_response_hex()}")

    buffer = b""
    try:
        while True:
            waiting = ser.in_waiting
            if waiting:
                buffer += ser.read(waiting)
            while len(buffer) >= RESPONSE_BYTES:
                challenge = buffer[:RESPONSE_BYTES]
                buffer = buffer[RESPONSE_BYTES:]
                response = puf.handle_exchange(challenge)
                ser.write(response)
                _log(
                    f"Serial: challenge={challenge.hex()[:32]}... "
                    f"-> response={response.hex()}"
                )
            time.sleep(0.01)
    except KeyboardInterrupt:
        _log("Stopping serial server...")
    finally:
        ser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Virtual Arduino PUF (128-bit)")
    parser.add_argument(
        "--mode",
        choices=("tcp", "serial"),
        default="tcp",
        help="tcp = localhost socket (default), serial = COM port",
    )
    parser.add_argument(
        "--host", default=DEFAULT_TCP_HOST, help="TCP bind host (tcp mode)"
    )
    parser.add_argument(
        "--port",
        default=str(DEFAULT_TCP_PORT),
        help="TCP port (tcp mode) or COM port name e.g. COM3 (serial mode)",
    )
    parser.add_argument(
        "--device-id",
        default="virtual-arduino-puf-001",
        help="Unique device ID (changes PUF fingerprint)",
    )
    parser.add_argument(
        "--baud", type=int, default=DEFAULT_BAUD, help="Serial baud rate"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Print one 128-bit response and exit",
    )
    args = parser.parse_args()

    puf = VirtualPUF(device_id=args.device_id)

    if args.test:
        response = puf.generate_response_hex()
        print(f"Challenge (128-bit): {DEFAULT_CHALLENGE.hex()}")
        print(f"Response  (128-bit): {response}")
        print(f"Response length: {len(response)} hex chars = {RESPONSE_BITS} bits")
        return 0

    if args.mode == "tcp":
        run_tcp_server(puf, host=args.host, port=int(args.port))
    else:
        run_serial_server(puf, port=args.port, baud=args.baud)
    return 0


if __name__ == "__main__":
    sys.exit(main())
