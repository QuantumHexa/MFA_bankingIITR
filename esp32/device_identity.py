# device_identity.py
# PUF-rooted X25519 device key (re-derived each boot; scalar never stored).

import gc

import config
from hkdf import derive_key
from key_derive import derive_puf_material, wipe_bytes
from x25519 import clamp_scalar, public_key_from_scalar, shared_secret

DEVICE_INFO = getattr(config, "MFA_DEVICE_INFO", b"esp32c6-mfa-device-x25519-v1")


def derive_device_scalar():
    puf_bytes, meta = derive_puf_material()
    if puf_bytes is None:
        return None, None, meta

    helper = meta["helper"]
    seed = derive_key(
        puf_bytes,
        bytes(helper["salt"]),
        DEVICE_INFO,
        32,
    )
    scalar = clamp_scalar(seed)
    wipe_bytes(seed)
    wipe_bytes(puf_bytes)
    gc.collect()
    return scalar, meta, None


def derive_device_public_key():
    scalar, meta, err = derive_device_scalar()
    if scalar is None:
        return None, err or meta

    pubkey = public_key_from_scalar(scalar)
    wipe_bytes(scalar)
    gc.collect()
    return pubkey, {"bit_errors": meta.get("bit_errors", 0)}


def compute_shared_secret(scalar, peer_public_bytes):
    secret = shared_secret(scalar, peer_public_bytes)
    wipe_bytes(scalar)
    return secret
