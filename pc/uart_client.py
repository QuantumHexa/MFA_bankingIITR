# uart_client.py
# Shared serial helpers for enroll + login clients.

import time
from typing import Optional

import serial
from serial.tools import list_ports

import protocol


def list_serial_ports() -> None:
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for info in ports:
        print("  {}  {}  [{}]".format(info.device, info.description, info.hwid))


def open_port(port: str, baud: int) -> serial.Serial:
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


def send_line(ser: serial.Serial, text: str) -> None:
    ser.write(text.encode("ascii"))
    ser.flush()


def read_line(ser: serial.Serial, timeout_s: Optional[float] = None) -> str:
    if timeout_s is None:
        timeout_s = protocol.UART_TIMEOUT_S
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
    raise TimeoutError("no response (timeout {:.1f}s)".format(timeout_s))


def wait_device_ready(
    ser: serial.Serial,
    expected: str = "mfa_enrolled",
    timeout_s: float = 20.0,
    verbose: bool = False,
) -> str:
    """Ping MFA:STATUS? repeatedly until the board answers."""
    deadline = time.monotonic() + timeout_s
    last_ping = 0.0

    while time.monotonic() < deadline:
        now = time.monotonic()
        if now - last_ping >= 0.4:
            send_line(ser, protocol.CMD_STATUS)
            last_ping = now

        try:
            line = read_line(ser, timeout_s=0.5)
        except TimeoutError:
            continue

        if verbose:
            print("  serial:", line)

        if line.startswith(protocol.PREFIX_STATUS_OK):
            status = protocol.parse_status(line)
            if status == expected:
                return status
            if expected == "mfa_enrolled" and status == "puf_ready":
                raise RuntimeError(
                    "device PUF is ready but MFA not enrolled — run enroll_client.py first"
                )
            raise RuntimeError(
                "device status is {!r}, expected {!r}".format(status, expected)
            )

        if line.startswith(">>>"):
            raise RuntimeError("ESP32 at REPL — deploy MFA main.py and reset.")

    raise TimeoutError(
        "device not ready (no MFA:STATUS response in {:.0f}s). "
        "Is MFA main.py running on the board?".format(timeout_s)
    )


def read_protocol_line(
    ser: serial.Serial,
    prefixes: tuple = protocol.RESPONSE_PREFIXES,
    timeout_s: Optional[float] = None,
    verbose: bool = False,
) -> str:
    if timeout_s is None:
        timeout_s = protocol.UART_TIMEOUT_S
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            line = read_line(ser, timeout_s=min(1.0, max(0.1, remaining)))
        except TimeoutError:
            continue
        if verbose:
            print("  serial:", line)
        if line.startswith(protocol.PREFIX_WORK):
            print("  device working:", line)
            continue
        if line.startswith(prefixes):
            return line
        if line.startswith(">>>"):
            raise RuntimeError("ESP32 at REPL — deploy MFA main.py and reset.")
    raise TimeoutError("no MFA protocol response (timeout {:.1f}s)".format(timeout_s))
