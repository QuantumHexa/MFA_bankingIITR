# gf256.py

class GF256:

    __slots__ = ("_exp", "_log")

    def __init__(self):
        self._exp = bytearray(512)
        self._log = bytearray(256)
        x = 1
        for i in range(255):
            self._exp[i] = x
            self._log[x] = i
            x <<= 1
            if x & 0x100:
                x ^= 0x11D
        for i in range(255, 512):
            self._exp[i] = self._exp[i - 255]

    def mul(self, a, b):
        if a == 0 or b == 0:
            return 0
        return self._exp[self._log[a] + self._log[b]]

    def div(self, a, b):
        if b == 0:
            raise ZeroDivisionError
        if a == 0:
            return 0
        return self._exp[(self._log[a] - self._log[b]) % 255]

    def inv(self, a):
        if a == 0:
            raise ZeroDivisionError
        return self._exp[255 - self._log[a]]

    def pow(self, a, n):
        if a == 0:
            return 0
        return self._exp[(self._log[a] * n) % 255]
