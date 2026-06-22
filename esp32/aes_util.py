# aes_util.py

from ucryptolib import aes as _aes
import os


def _pad(data, bs=16):
    n = bs - (len(data) % bs)
    return data + bytes([n] * n)


def _unpad(data):
    n = data[-1]
    if n < 1 or n > 16 or data[-n:] != bytes([n] * n):
        raise ValueError("bad padding")
    return data[:-n]


def encrypt(plaintext, key):
    iv = os.urandom(16)
    ct = _aes(key, 2, iv).encrypt(_pad(plaintext))
    return iv + ct


def decrypt(blob, key):
    iv, ct = blob[:16], blob[16:]
    return _unpad(_aes(key, 2, iv).decrypt(ct))
