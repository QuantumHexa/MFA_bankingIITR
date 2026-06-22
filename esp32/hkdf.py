# hkdf.py

import uhashlib as _hl


def _hmac_sha256(key, msg):
    BS = 64
    if len(key) > BS:
        key = _hl.sha256(key).digest()
    kb = bytearray(BS)
    kb[:len(key)] = key
    ipad = bytearray(BS)
    opad = bytearray(BS)
    for i in range(BS):
        ipad[i] = kb[i] ^ 0x36
        opad[i] = kb[i] ^ 0x5C
    inner = _hl.sha256(bytes(ipad) + bytes(msg)).digest()
    return _hl.sha256(bytes(opad) + inner).digest()


def hkdf_extract(salt, ikm):
    if not salt:
        salt = b"\x00" * 32
    return _hmac_sha256(salt, ikm)


def hkdf_expand(prk, info, length):
    n = (length + 31) // 32
    okm = b""
    prev = b""
    for i in range(1, n + 1):
        prev = _hmac_sha256(prk, prev + info + bytes([i]))
        okm += prev
    return okm[:length]


def derive_key(puf_bytes, salt, info, length=16):
    return hkdf_expand(hkdf_extract(salt, puf_bytes), info, length)
