# config.py
# PUF + MFA device authentication parameters.

RTC_BASE = 0x5000_0000
RTC_SIZE = 8192

PUF_RAW_WORDS = 32
PUF_TARGET_BITS = 255
ENROLL_SAMPLES = 30
STABLE_THRESH = 0.90

BCH_T = 10

HKDF_SALT_LEN = 32
HKDF_INFO = b"esp32c6-puf-aes128-v1"
AES_KEY_LEN = 16

# PUF-rooted X25519 device identity (separate from banking AES key)
MFA_DEVICE_INFO = b"esp32c6-mfa-device-x25519-v1"
MFA_PROOF_INFO = b"esp32c6-mfa-login-proof-v1"

NONCE_LEN = 16
UART_BAUD = 115200
UART_TIMEOUT_MS = 8000

FILE_ROOT = "/"
FILE_HELPER = FILE_ROOT + "puf_helper.json"
FILE_ENROLLED = FILE_ROOT + ".puf_enrolled"
FILE_SAMPLES = FILE_ROOT + "puf_samples.json"
FILE_MFA = FILE_ROOT + "mfa_enrollment.json"
