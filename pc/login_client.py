#!/usr/bin/env python3
# login_client.py
# Simulated net-banking login with PUF device MFA (factor 2).
#
#   python login_client.py --port COM5 --customer CUST10042 --password secret

import argparse
import secrets
import sys
import time

import device_registry
import mfa_auth
import protocol
import uart_client
import x25519_util


def fetch_live_device_pubkey(ser, verbose=False) -> bytes:
    uart_client.send_line(ser, protocol.CMD_PUBKEY)
    line = uart_client.read_protocol_line(ser, verbose=verbose)
    hex_key = protocol.parse_pubkey_response(line)
    return bytes.fromhex(hex_key)


def simulate_password_check(customer_id: str, password: str) -> bool:
    return len(password) >= 4


def main() -> int:
    parser = argparse.ArgumentParser(description="Net banking login + PUF device MFA")
    parser.add_argument("--port", "-p", help="serial port")
    parser.add_argument("--list-ports", action="store_true")
    parser.add_argument("--baud", "-b", type=int, default=protocol.UART_BAUD)
    parser.add_argument("--customer", "-c", default="CUST10042")
    parser.add_argument("--password", default="demo1234", help="simulated password")
    parser.add_argument("--verbose", "-v", action="store_true", help="show serial lines")
    args = parser.parse_args()

    if args.list_ports:
        uart_client.list_serial_ports()
        return 0
    if not args.port:
        parser.error("--port required")

    try:
        device_pubkey = device_registry.get_device_pubkey(args.customer)
    except KeyError as exc:
        print("Error:", exc, file=sys.stderr)
        print("Run enroll_client.py first.")
        return 1

    print("=== Net Banking Login (lab) ===")
    print("Step 1 — password (something you know)")
    if not simulate_password_check(args.customer, args.password):
        print("Password rejected.")
        return 1
    print("Password OK for", args.customer)

    login_id = "LOGIN-" + secrets.token_hex(8)
    print("\nStep 2 — PUF device MFA (something you have)")
    print("Login session:", login_id)

    eph_scalar, eph_public = x25519_util.generate_ephemeral_keypair()
    nonce = x25519_util.make_nonce()

    auth_line = "MFA:AUTH:{}:{}:{}:{}".format(
        login_id,
        args.customer,
        eph_public.hex(),
        nonce.hex(),
    )

    try:
        with uart_client.open_port(args.port, args.baud) as ser:
            status = uart_client.wait_device_ready(
                ser, expected="mfa_enrolled", verbose=args.verbose
            )
            print("Device ready:", status)

            live_pubkey = fetch_live_device_pubkey(ser, verbose=args.verbose)
            stored_hex = device_pubkey.hex()
            live_hex = live_pubkey.hex()
            if live_hex != stored_hex:
                print("Updating stored device pubkey (was out of date).")
                if args.verbose:
                    print("  registry:", stored_hex[:32], "…")
                    print("  live    :", live_hex[:32], "…")
                device_registry.register_device(args.customer, live_hex)
                device_pubkey = live_pubkey
            else:
                print("Device pubkey matches registry.")

            ser.reset_input_buffer()

            print("Requesting device proof from", args.port, "…")
            print("(PUF + X25519 on device may take several seconds)")
            t0 = time.monotonic()
            uart_client.send_line(ser, auth_line + "\n")
            line = uart_client.read_protocol_line(
                ser,
                prefixes=protocol.AUTH_WAIT_PREFIXES,
                timeout_s=120.0,
                verbose=args.verbose,
            )
            proof = protocol.parse_proof_response(line)
            elapsed = time.monotonic() - t0

            shared = x25519_util.shared_secret(eph_scalar, device_pubkey)
            if args.verbose:
                print("  shared  :", shared.hex()[:32], "…")
            mfa_auth.verify_login_proof(shared, login_id, args.customer, nonce, proof)

            print("Device proof verified in {:.2f}s".format(elapsed))
            print("\n=== LOGIN SUCCESS ===")
            print("Factors: password + PUF hardware device")
            print("Customer:", args.customer)
            print("Session :", login_id)
    except Exception as exc:
        print("Error:", exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
