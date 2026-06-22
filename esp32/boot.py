# boot.py

from machine import mem32
import puf_state

_RTC = 0x5000_0000
_NW = 32

puf_state.raw = bytearray(_NW * 4)
for _i in range(_NW):
    _v = mem32[_RTC + _i * 4]
    puf_state.raw[_i * 4] = _v & 0xFF
    puf_state.raw[_i * 4 + 1] = (_v >> 8) & 0xFF
    puf_state.raw[_i * 4 + 2] = (_v >> 16) & 0xFF
    puf_state.raw[_i * 4 + 3] = (_v >> 24) & 0xFF

del _i, _v, _RTC, _NW
