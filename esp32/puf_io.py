# puf_io.py

from machine import mem32
import config


def read_raw(n_words=None):
    if n_words is None:
        n_words = config.PUF_RAW_WORDS
    buf = bytearray(n_words * 4)
    for i in range(n_words):
        v = mem32[config.RTC_BASE + i * 4]
        buf[i * 4] = v & 0xFF
        buf[i * 4 + 1] = (v >> 8) & 0xFF
        buf[i * 4 + 2] = (v >> 16) & 0xFF
        buf[i * 4 + 3] = (v >> 24) & 0xFF
    return buf


def extract_word(raw_bytes, positions, n_bits):
    word = 0
    for i in range(n_bits):
        bp = positions[i]
        if raw_bytes[bp >> 3] & (1 << (bp & 7)):
            word |= 1 << i
    return word


def find_stable_bits(samples, n_bits, threshold=None):
    if threshold is None:
        threshold = config.STABLE_THRESH

    n_samp = len(samples)
    bit_len = len(samples[0]) * 8
    ones = [0] * bit_len
    for s in samples:
        for bp in range(bit_len):
            if s[bp >> 3] & (1 << (bp & 7)):
                ones[bp] += 1

    scored = []
    for bp in range(bit_len):
        p = ones[bp] / n_samp
        stab = p if p >= 0.5 else 1.0 - p
        scored.append((stab, bp))
    scored.sort(key=lambda x: -x[0])

    selected = []
    for stab, bp in scored:
        if stab < threshold:
            break
        selected.append(bp)
        if len(selected) >= n_bits:
            break
    return selected


def majority_value(samples, bit_pos):
    ones = sum(
        1 for s in samples
        if s[bit_pos >> 3] & (1 << (bit_pos & 7))
    )
    return 1 if ones > len(samples) // 2 else 0
