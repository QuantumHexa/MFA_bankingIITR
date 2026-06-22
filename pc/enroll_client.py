#!/usr/bin/env python3
# enroll_client.py
# Register a PUF MFA device for a net-banking customer (lab flow).
#
#   python enroll_client.py --port COM5 --customer CUST10042

import argparse
import sys

import serial

import device_registry
import protocol
import uart_client


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll PUF MFA device for a customer")
    parser.add_argument("--port", "-p", help="serial port")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--baud", "-b", type=int, default=protocol.UART_BAUD)
    parser.add_argument(
        "--customer", "-c", default="CUST10042",
        help="bank customer identifier",
    )
    args = parser.parse_args()

    if args.list_ports:
        uart_client.list_serial_ports()
        return 0
    if not args.port:
        parser.error("--port required")

    try:
        with uart_client.open_port(args.port, args.baud) as ser:
            print("Connected to", args.port)
            uart_client.send_line(ser, protocol.CMD_STATUS)
            status = protocol.parse_status(uart_client.read_protocol_line(ser))
            print("Device status:", status)

            if status == "puf_not_enrolled":
                print("Run PUF enrollment (Code/main.py) first.")
                return 1

            print("Enrolling customer", args.customer, "…")
            uart_client.send_line(ser, protocol.CMD_ENROLL + args.customer + "\n")
            line = uart_client.read_protocol_line(ser)
            customer_id, pubkey_hex = protocol.parse_enroll_response(line)

            device_registry.register_device(customer_id, pubkey_hex)
            print("Enrollment OK")
            print("  Customer   :", customer_id)
            print("  Device pubkey:", pubkey_hex[:32], "…")
            print("  Saved to   : device_registry.json")
    except (serial.SerialException, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
