# key_derive.py
# PUF reconstruction + stable material for MFA / AES.

import gc

import config
import puf_state
from puf_io import extract_word
from bch import BCH
from sketch import SecureSketch, load_helper
from hkdf import derive_key


def is_enrolled():
    try:
        with open(config.FILE_ENROLLED):
            return True
    except OSError:
        return False


def derive_puf_material():
    """Return (puf_bytes, meta) or (None, error_code)."""
    if not is_enrolled():
        return None, "not_enrolled"

    raw = puf_state.raw
    if raw is None:
        return None, "no_puf_data"

    try:
        helper = load_helper()
    except (OSError, ValueError):
        return None, "no_helper"

    positions = helper["positions"]
    n_bits = helper["wl"]
    t = helper["t"]

    noisy_word = extract_word(raw, positions, n_bits)
    bch = BCH(t)
    sketch = SecureSketch(bch, n_bits)
    stable_word = sketch.reconstruct(noisy_word, helper)
    if stable_word is None:
        return None, "reconstruct_failed"

    bit_errors = bin(noisy_word ^ stable_word).count("1")
    puf_bytes = stable_word.to_bytes((n_bits + 7) // 8, "little")
    meta = {"bit_errors": bit_errors, "helper": helper}
    del stable_word, noisy_word
    gc.collect()
    return puf_bytes, meta


def derive_stable_aes_key():
    puf_bytes, meta = derive_puf_material()
    if puf_bytes is None:
        return None, meta

    helper = meta["helper"]
    key = derive_key(
        puf_bytes,
        bytes(helper["salt"]),
        config.HKDF_INFO,
        config.AES_KEY_LEN,
    )
    bit_errors = meta["bit_errors"]
    del puf_bytes
    gc.collect()
    return key, {"bit_errors": bit_errors}


def wipe_bytes(buf):
    if buf is None:
        return
    if isinstance(buf, int):
        return
    b = bytearray(buf)
    for i in range(len(b)):
        b[i] = 0
    del b
    gc.collect()
