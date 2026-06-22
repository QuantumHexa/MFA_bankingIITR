# device_registry.py
# Bank-side record: customer_id -> PUF device public key.

import json
import os
import time


DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "device_registry.json")


def load_registry(path: str = DEFAULT_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_registry(data: dict, path: str = DEFAULT_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def register_device(customer_id: str, device_pubkey_hex: str, path: str = DEFAULT_PATH) -> None:
    registry = load_registry(path)
    registry[customer_id] = {
        "device_pubkey": device_pubkey_hex,
        "enrolled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_registry(registry, path)


def get_device_pubkey(customer_id: str, path: str = DEFAULT_PATH) -> bytes:
    registry = load_registry(path)
    if customer_id not in registry:
        raise KeyError("customer {!r} not registered".format(customer_id))
    return bytes.fromhex(registry[customer_id]["device_pubkey"])
