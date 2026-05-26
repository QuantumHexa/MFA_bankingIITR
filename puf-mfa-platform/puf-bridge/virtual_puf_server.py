#!/usr/bin/env python3
"""Virtual PUF bridge — adapted from version_8 virtual_puf.py"""

import argparse
import hashlib
import hmac
import socket
import sys
import threading
import time

DEFAULT_CHALLENGE = bytes.fromhex("ffc3330ff0aacc30ff0aacc01ffc3301")
RESPONSE_BYTES = 16
DEFAULT_TCP_HOST = "0.0.0.0"
DEFAULT_TCP_PORT = 8765


class VirtualPUF:
    def __init__(self, device_id: str = "virtual-cmod-a7-001"):
        self.device_id = device_id
        self._secret = hashlib.sha256(device_id.encode()).digest()

    def generate_response(self, challenge: bytes) -> bytes:
        challenge = challenge[:RESPONSE_BYTES].ljust(RESPONSE_BYTES, b"\x00")
        return hmac.new(self._secret, challenge, hashlib.sha256).digest()[:RESPONSE_BYTES]


def _handle_client(puf: VirtualPUF, conn: socket.socket, addr) -> None:
    try:
        while True:
            challenge = b""
            while len(challenge) < RESPONSE_BYTES:
                chunk = conn.recv(RESPONSE_BYTES - len(challenge))
                if not chunk:
                    return
                challenge += chunk
            response = puf.generate_response(challenge)
            conn.sendall(response)
            print(f"[{addr}] C={challenge.hex()} R={response.hex()}", flush=True)
    except OSError:
        pass
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_TCP_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_TCP_PORT)
    parser.add_argument("--device-id", default="virtual-cmod-a7-001")
    args = parser.parse_args()

    puf = VirtualPUF(args.device_id)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(5)
    print(f"Virtual PUF on {args.host}:{args.port} device={args.device_id}", flush=True)

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=_handle_client, args=(puf, conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
