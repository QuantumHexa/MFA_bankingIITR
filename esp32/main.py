# main.py
# MFA device authentication server over USB serial.
#
# Enrollment (link device to customer):
#   MFA:ENROLL:<customer_id>
#   -> MFA:ENROLL:OK:<customer_id>:<device_pubkey_hex>
#
# Login MFA step (after password on PC):
#   MFA:AUTH:<login_id>:<customer_id>:<pc_ephemeral_pubkey_hex>:<nonce_hex>
#   -> MFA:PROOF:OK:<hmac_hex>
#
# Requires prior PUF enrollment (puf_helper.json + .puf_enrolled).

import gc
import sys
import time
import uselect

import mfa_protocol as proto
from key_derive import is_enrolled, wipe_bytes

# Backward compatible if an older mfa_protocol.py is still on the board.
if not hasattr(proto, "PREFIX_WORK"):
    proto.PREFIX_WORK = b"MFA:WORK:"
if not hasattr(proto, "PREFIX_PUBKEY_OK"):
    proto.PREFIX_PUBKEY_OK = b"MFA:PUBKEY:OK:"
if not hasattr(proto, "CMD_PUBKEY"):
    proto.CMD_PUBKEY = b"MFA:PUBKEY?\n"
from device_identity import derive_device_scalar, derive_device_public_key, compute_shared_secret
from mfa_store import save_mfa_record, has_mfa_enrollment, get_customer_id, load_mfa_record
from mfa_auth import compute_login_proof

_poll = uselect.poll()
_poll.register(sys.stdin, uselect.POLLIN)

_rx_buf = b""


def _feed_rx():
    global _rx_buf
    # Never call sys.stdin.read() without a size — it blocks on MicroPython ESP32.
    while _poll.poll(0):
        chunk = sys.stdin.read(1)
        if not chunk:
            break
        if isinstance(chunk, str):
            chunk = chunk.encode()
        _rx_buf += chunk


def _pop_line():
    global _rx_buf
    if b"\n" not in _rx_buf:
        return None
    line, _, _rx_buf = _rx_buf.partition(b"\n")
    return line.rstrip(b"\r\n") + b"\n"


def _read_line(timeout_ms=None):
    """Legacy helper — prefer _feed_rx/_pop_line in the main loop."""
    if timeout_ms is None:
        timeout_ms = proto.UART_TIMEOUT_MS
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        _feed_rx()
        line = _pop_line()
        if line:
            return line
        time.sleep_ms(1)
    return None


def _write_line(data):
    if not data.endswith(b"\n"):
        data += b"\n"
    sys.stdout.write(data)
    try:
        sys.stdout.flush()
    except AttributeError:
        pass


def _write_err(reason):
    _write_line(proto.PREFIX_ERR + reason.encode())


def _status():
    if not is_enrolled():
        return b"puf_not_enrolled"
    if not has_mfa_enrollment():
        return b"puf_ready"
    return b"mfa_enrolled"


def _handle_status():
    _write_line(proto.PREFIX_STATUS_OK + _status())


def _handle_pubkey():
    if not is_enrolled():
        _write_err("puf_not_enrolled")
        return
    pubkey, info = derive_device_public_key()
    if pubkey is None:
        _write_err(info if isinstance(info, str) else "derive_failed")
        return
    _write_line(proto.PREFIX_PUBKEY_OK + pubkey.hex().encode())
    wipe_bytes(pubkey)
    gc.collect()


def _handle_enroll(line):
    if not is_enrolled():
        _write_err("puf_not_enrolled")
        return

    customer_id = line[len(proto.CMD_ENROLL):-1].decode()
    if not customer_id or len(customer_id) > 64:
        _write_err("bad_customer_id")
        return

    pubkey, info = derive_device_public_key()
    if pubkey is None:
        _write_err(info if isinstance(info, str) else "derive_failed")
        return

    pubkey_hex = pubkey.hex()
    save_mfa_record(customer_id, pubkey_hex)

    body = customer_id.encode() + b":" + pubkey_hex.encode()
    _write_line(proto.PREFIX_ENROLL_OK + body)
    if isinstance(info, dict) and "bit_errors" in info:
        print("MFA enrolled ({} bit-errors corrected)".format(info["bit_errors"]))
    wipe_bytes(pubkey)
    gc.collect()


def _handle_auth(line):
    if not is_enrolled():
        _write_err("puf_not_enrolled")
        return
    if not has_mfa_enrollment():
        _write_err("not_mfa_enrolled")
        return

    payload = line[len(proto.CMD_AUTH):-1].decode().lstrip(":")
    parts = payload.split(":")
    if len(parts) != 4:
        _write_err("bad_auth_format")
        return

    login_id, customer_id, eph_pub_hex, nonce_hex = parts
    record = load_mfa_record()
    if customer_id != record["customer_id"]:
        _write_err("customer_mismatch")
        return

    if len(eph_pub_hex) != proto.PUBKEY_HEX_LEN or len(nonce_hex) != proto.NONCE_HEX_LEN:
        _write_err("bad_field_length")
        return

    try:
        eph_pub = bytes.fromhex(eph_pub_hex)
        nonce = bytes.fromhex(nonce_hex)
    except ValueError:
        _write_err("bad_hex")
        return

    _write_line(proto.PREFIX_WORK + b"auth")
    print("AUTH processing", login_id)

    shared = None
    try:
        gc.collect()
        scalar, meta, err = derive_device_scalar()
        if scalar is None:
            err_text = err if isinstance(err, str) else (meta if isinstance(meta, str) else "derive_failed")
            _write_err(err_text)
            return

        gc.collect()
        t0 = time.ticks_ms()
        shared = compute_shared_secret(scalar, eph_pub)
        proof = compute_login_proof(shared, login_id, customer_id, nonce)
        dt = time.ticks_diff(time.ticks_ms(), t0)
        _write_line(proto.PREFIX_PROOF_OK + proof.hex().encode())
        print("MFA proof sent in {} ms".format(dt))
        if isinstance(meta, dict) and "bit_errors" in meta:
            print("PUF bit-errors corrected:", meta["bit_errors"])
    except Exception as exc:
        exc_name = type(exc).__name__
        _write_err("auth_failed:" + exc_name)
        print("AUTH exception:", exc_name, exc)
        try:
            sys.stdout.flush()
        except AttributeError:
            pass
    finally:
        wipe_bytes(shared)
        gc.collect()


def _dispatch(line):
    # Ignore empty lines and serial noise (e.g. \r from COM port open).
    if not line or line in (b"\n", b"\r\n"):
        return
    if not line.startswith(b"MFA:"):
        return

    if line == proto.CMD_STATUS:
        _handle_status()
    elif line == proto.CMD_PUBKEY:
        _handle_pubkey()
    elif line.startswith(proto.CMD_ENROLL):
        _handle_enroll(line)
    elif line.startswith(proto.CMD_AUTH):
        _handle_auth(line)
    else:
        _write_err("unknown_command")


def main():
    print("MFA PUF device server  baud={}".format(proto.UART_BAUD))
    print("Status:", _status().decode())
    if is_enrolled() and has_mfa_enrollment():
        print("Customer:", get_customer_id())

    while True:
        _feed_rx()
        line = _pop_line()
        if line:
            _dispatch(line)
        time.sleep_ms(1)


main()
