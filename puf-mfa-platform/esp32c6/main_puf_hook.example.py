"""
Add these lines to the PDF project's main.py AFTER successful reconstruction.

This lets puf_serial_server.py read the reconstructed AES-128 key.

Example (at end of reconstruct() in main.py):

    global AES_KEY
    AES_KEY = key_bytes  # 16 bytes from HKDF / sketch output

Then add:

def get_aes_key_bytes():
    return AES_KEY
"""

AES_KEY = None


def get_aes_key_bytes():
    if AES_KEY is None or len(AES_KEY) < 16:
        raise RuntimeError("AES key not available — run reconstruction first")
    return AES_KEY
