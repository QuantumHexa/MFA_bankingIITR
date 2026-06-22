# bch.py

from gf256 import GF256


def _bitlen(n):
    if n == 0:
        return 0
    bl = 0
    while n:
        n >>= 1
        bl += 1
    return bl


class BCH:

    def __init__(self, t):
        self.t = t
        self.n = 255
        self.gf = GF256()
        self.g = self._build_gen_poly()
        self.nsyn = BCH._deg(self.g)
        self.k = self.n - self.nsyn

    @staticmethod
    def _deg(p):
        return _bitlen(p) - 1 if p else -1

    @staticmethod
    def _gf2_mul(a, b):
        r = 0
        s = 0
        while b:
            if b & 1:
                r ^= a << s
            b >>= 1
            s += 1
        return r

    @staticmethod
    def _gf2_mod(a, b):
        db = _bitlen(b) - 1
        while True:
            da = _bitlen(a)
            if da == 0:
                return a
            da -= 1
            if da < db:
                return a
            a ^= b << (da - db)

    def _build_gen_poly(self):
        g = 1
        seen = set()
        for i in range(1, 2 * self.t + 1, 2):
            mp = self._minimal_poly(i)
            if mp not in seen:
                seen.add(mp)
                g = self._gf2_mul(g, mp)
        return g

    def _minimal_poly(self, exp):
        c = exp % 255
        conj = []
        visited = set()
        while c not in visited:
            visited.add(c)
            conj.append(c)
            c = (c << 1) % 255
        coeffs = [1]
        for c in conj:
            root = self.gf._exp[c]
            nxt = [0] * (len(coeffs) + 1)
            for j in range(len(coeffs)):
                nxt[j + 1] ^= coeffs[j]
                nxt[j] ^= self.gf.mul(root, coeffs[j])
            coeffs = nxt
        p = 0
        for j, v in enumerate(coeffs):
            assert v in (0, 1)
            if v:
                p |= 1 << j
        return p

    def syndrome(self, word):
        syn = []
        for i in range(1, 2 * self.t + 1, 2):
            ai = self.gf._exp[i % 255]
            s = 0
            xp = 1
            w = word
            while w:
                if w & 1:
                    s ^= xp
                w >>= 1
                xp = self.gf.mul(xp, ai)
            syn.append(s)
        return syn

    def _berlekamp_massey(self, syn):
        gf = self.gf
        sigma = [1]
        B = [1]
        L = 0
        r_prev = -1
        b = 1
        for i in range(self.t):
            delta = syn[i]
            for j in range(1, L + 1):
                if j < len(sigma):
                    delta ^= gf.mul(sigma[j], syn[i - j])
            if delta == 0:
                continue
            T = sigma[:]
            coeff = gf.div(delta, b)
            shift = i - r_prev
            need = len(B) + shift
            while len(sigma) < need:
                sigma.append(0)
            for j in range(len(B)):
                sigma[j + shift] ^= gf.mul(coeff, B[j])
            if 2 * L <= i:
                L = i + 1 - L
                B = T
                r_prev = i
                b = delta
        while len(sigma) > 1 and sigma[-1] == 0:
            sigma.pop()
        return sigma

    def _chien_search(self, sigma):
        gf = self.gf
        deg = len(sigma) - 1
        errs = []
        for j in range(self.n):
            aj = gf._exp[(255 - j) % 255]
            v = sigma[deg]
            for i in range(deg - 1, -1, -1):
                v = gf.mul(v, aj) ^ sigma[i]
            if v == 0:
                errs.append(j)
        return errs if len(errs) == deg else None

    def decode(self, syn_diff):
        if all(s == 0 for s in syn_diff):
            return []
        sigma = self._berlekamp_massey(syn_diff)
        if sigma is None or (len(sigma) - 1) > self.t:
            return None
        return self._chien_search(sigma)
