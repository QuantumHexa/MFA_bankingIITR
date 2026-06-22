# sketch.py

import ujson as json
from bch import BCH
import config


class SecureSketch:

    def __init__(self, bch_codec, word_len):
        self.bch = bch_codec
        self.wl = word_len

    def enroll(self, puf_word):
        syn = self.bch.syndrome(puf_word)
        return {"syn": syn, "wl": self.wl, "t": self.bch.t}

    def reconstruct(self, puf_word_noisy, helper):
        if helper["wl"] != self.wl or helper["t"] != self.bch.t:
            raise ValueError("helper mismatch")
        syn_ref = helper["syn"]
        syn_curr = self.bch.syndrome(puf_word_noisy)
        delta = [a ^ b for a, b in zip(syn_ref, syn_curr)]
        err_pos = self.bch.decode(delta)
        if err_pos is None:
            return None
        corrected = puf_word_noisy
        for p in err_pos:
            corrected ^= 1 << p
        return corrected


def save_helper(helper, path=None):
    with open(path or config.FILE_HELPER, "w") as f:
        json.dump(helper, f)


def load_helper(path=None):
    with open(path or config.FILE_HELPER) as f:
        return json.load(f)
