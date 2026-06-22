# mfa_store.py

import ujson as json

import config


def save_mfa_record(customer_id, device_pubkey_hex):
    record = {
        "customer_id": customer_id,
        "device_pubkey": device_pubkey_hex,
        "ver": 1,
    }
    with open(config.FILE_MFA, "w") as f:
        json.dump(record, f)


def load_mfa_record():
    with open(config.FILE_MFA) as f:
        return json.load(f)


def has_mfa_enrollment():
    try:
        load_mfa_record()
        return True
    except (OSError, ValueError, KeyError):
        return False


def get_customer_id():
    try:
        return load_mfa_record()["customer_id"]
    except (OSError, ValueError, KeyError):
        return None
