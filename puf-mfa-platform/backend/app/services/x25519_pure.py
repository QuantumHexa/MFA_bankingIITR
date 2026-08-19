# x25519_pure.py
# Must match esp32/x25519.py byte-for-byte in behaviour.

P = 2**255 - 19
BASE_POINT = 9
A24 = 121665


def _cswap(swap, a, b):
    dummy = swap * (a - b)
    return a - dummy, b + dummy


def clamp_scalar(k_bytes):
    k = bytearray(k_bytes[:32])
    while len(k) < 32:
        k.append(0)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return int.from_bytes(k, "little")


def int_to_bytes32(value):
    value = value % P
    out = bytearray(32)
    for i in range(32):
        out[i] = value & 0xFF
        value >>= 8
    out[31] &= 0x7F
    return bytes(out)


def decode_u_coordinate(peer_public_bytes):
    peer = bytearray(peer_public_bytes[:32])
    while len(peer) < 32:
        peer.append(0)
    peer[31] &= 0x7F
    return bytes32_to_int(bytes(peer))


def bytes32_to_int(data):
    buf = data[:32]
    if len(buf) < 32:
        buf = buf + b"\x00" * (32 - len(buf))
    n = 0
    for i in range(31, -1, -1):
        n = (n << 8) | buf[i]
    return n


def x25519(scalar, u_coordinate=BASE_POINT):
    x_1 = u_coordinate
    x_2 = 1
    z_2 = 0
    x_3 = u_coordinate
    z_3 = 1
    swap = 0

    for t in reversed(range(255)):
        k_t = (scalar >> t) & 1
        swap ^= k_t
        x_2, x_3 = _cswap(swap, x_2, x_3)
        z_2, z_3 = _cswap(swap, z_2, z_3)
        swap = k_t

        a = (x_2 + z_2) % P
        aa = pow(a, 2, P)
        b = (x_2 - z_2) % P
        bb = pow(b, 2, P)
        e = (aa - bb) % P
        c = (x_3 + z_3) % P
        d = (x_3 - z_3) % P
        da = (d * a) % P
        cb = (c * b) % P

        x_3 = pow(da + cb, 2, P)
        z_3 = (x_1 * pow(da - cb, 2, P)) % P
        x_2 = (aa * bb) % P
        z_2 = (e * (aa + A24 * e)) % P

    x_2, x_3 = _cswap(swap, x_2, x_3)
    z_2, z_3 = _cswap(swap, z_2, z_3)

    z_inv = pow(z_2, P - 2, P) if (z_2 % P) else 0
    return (x_2 * z_inv) % P


def public_key_from_scalar(scalar_int):
    return int_to_bytes32(x25519(scalar_int, BASE_POINT))


def scalar_to_hex(scalar_int: int) -> str:
    """64 hex chars, little-endian 32 bytes. Do not use int.hex() (adds 0x and can exceed VARCHAR(64))."""
    return int(scalar_int).to_bytes(32, "little").hex()


def scalar_from_hex(hex_str: str) -> int:
    text = (hex_str or "").strip().lower()
    if text.startswith("0x"):
        return int(text, 16)
    return int.from_bytes(bytes.fromhex(text), "little")


def shared_secret(scalar_int, peer_public_bytes):
    if isinstance(scalar_int, (bytes, bytearray)):
        scalar_int = int.from_bytes(scalar_int, "little")
    u = decode_u_coordinate(peer_public_bytes)
    return int_to_bytes32(x25519(scalar_int, u))
