#!/usr/bin/env python3
"""Quick test: send a challenge to ESP32 on serial and print the response."""

import argparse
import secrets
import sys
import time

try:
    import serial
except ImportError:
    print("Install pyserial: pip install pyserial")
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test ESP32 hardware PUF serial protocol")
    parser.add_argument("--port", default="COM3", help="Serial port (e.g. COM5 on Windows)")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    challenge = secrets.token_bytes(16)
    print(f"Port: {args.port} @ {args.baud}")
    print(f"Challenge: {challenge.hex()}")

    ser = serial.Serial(args.port, args.baud, timeout=5)
    try:
        ser.reset_input_buffer()
        ser.write(challenge)
        ser.flush()
        time.sleep(1.5)

        data = b""
        deadline = time.time() + 5
        while len(data) < 16 and time.time() < deadline:
            waiting = ser.in_waiting
            if waiting:
                data += ser.read(min(waiting, 16 - len(data)))
            else:
                time.sleep(0.05)

        if len(data) < 16:
            print("FAIL: no 16-byte response (got", len(data), "bytes)")
            if data:
                print("Partial:", data.hex())
            return 1

        print(f"Response:  {data.hex()}")
        print("OK — ESP32 hardware PUF serial link works")
        return 0
    finally:
        ser.close()


if __name__ == "__main__":
    raise SystemExit(main())
