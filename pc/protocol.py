# protocol.py

UART_BAUD = 115200
UART_TIMEOUT_S = 8.0

NONCE_HEX_LEN = 32
PUBKEY_HEX_LEN = 64
PROOF_HEX_LEN = 64

MFA_PROOF_INFO = b"esp32c6-mfa-login-proof-v1"

CMD_STATUS = "MFA:STATUS?\n"
CMD_ENROLL = "MFA:ENROLL:"
CMD_AUTH = "MFA:AUTH:"
CMD_PUBKEY = "MFA:PUBKEY?\n"

PREFIX_STATUS_OK = "MFA:STATUS:OK:"
PREFIX_ERR = "MFA:ERR:"
PREFIX_ENROLL_OK = "MFA:ENROLL:OK:"
PREFIX_PROOF_OK = "MFA:PROOF:OK:"
PREFIX_PUBKEY_OK = "MFA:PUBKEY:OK:"
PREFIX_WORK = "MFA:WORK:"

RESPONSE_PREFIXES = (
    PREFIX_STATUS_OK,
    PREFIX_ERR,
    PREFIX_ENROLL_OK,
    PREFIX_PROOF_OK,
    PREFIX_PUBKEY_OK,
)

AUTH_WAIT_PREFIXES = (PREFIX_PROOF_OK, PREFIX_ERR)


def parse_status(line: str) -> str:
    line = line.strip()
    if line.startswith(PREFIX_STATUS_OK):
        return line[len(PREFIX_STATUS_OK):]
    raise ValueError("unexpected status: {!r}".format(line))


def parse_enroll_response(line: str) -> tuple:
    line = line.strip()
    if not line.startswith(PREFIX_ENROLL_OK):
        if line.startswith(PREFIX_ERR):
            raise RuntimeError(line[len(PREFIX_ERR):])
        raise ValueError("unexpected enroll response: {!r}".format(line))
    body = line[len(PREFIX_ENROLL_OK):]
    customer_id, _, pubkey_hex = body.partition(":")
    if len(pubkey_hex) != PUBKEY_HEX_LEN:
        raise ValueError("bad pubkey length")
    return customer_id, pubkey_hex


def parse_pubkey_response(line: str) -> str:
    line = line.strip()
    if line.startswith(PREFIX_PUBKEY_OK):
        hex_key = line[len(PREFIX_PUBKEY_OK):]
        if len(hex_key) != PUBKEY_HEX_LEN:
            raise ValueError("bad pubkey length")
        return hex_key
    if line.startswith(PREFIX_ERR):
        raise RuntimeError(line[len(PREFIX_ERR):])
    raise ValueError("unexpected pubkey response: {!r}".format(line))


def parse_proof_response(line: str) -> bytes:
    line = line.strip()
    if line.startswith(PREFIX_PROOF_OK):
        proof_hex = line[len(PREFIX_PROOF_OK):]
        if len(proof_hex) != PROOF_HEX_LEN:
            raise ValueError("bad proof length")
        return bytes.fromhex(proof_hex)
    if line.startswith(PREFIX_ERR):
        raise RuntimeError(line[len(PREFIX_ERR):])
    raise ValueError("unexpected proof response: {!r}".format(line))
