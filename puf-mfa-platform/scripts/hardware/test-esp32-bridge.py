#!/usr/bin/env python3
"""Unit tests for ESP32 MFA bridge (no real serial port required)."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Allow importing backend app from repo layout
BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services import esp32_mfa_bridge, x25519_pure  # noqa: E402


class TestX25519Pure(unittest.TestCase):
    def test_shared_secret_symmetry(self):
        scalar_a = x25519_pure.clamp_scalar(os.urandom(32))
        scalar_b = x25519_pure.clamp_scalar(os.urandom(32))
        pub_a = x25519_pure.public_key_from_scalar(scalar_a)
        pub_b = x25519_pure.public_key_from_scalar(scalar_b)
        secret_ab = x25519_pure.shared_secret(scalar_a, pub_b)
        secret_ba = x25519_pure.shared_secret(scalar_b, pub_a)
        self.assertEqual(secret_ab, secret_ba)

    def test_scalar_hex_roundtrip_and_public_recompute(self):
        scalar = x25519_pure.clamp_scalar(os.urandom(32))
        pub = x25519_pure.public_key_from_scalar(scalar)
        stored = x25519_pure.scalar_to_hex(scalar)
        self.assertEqual(len(stored), 64)
        self.assertFalse(stored.startswith("0x"))
        restored = x25519_pure.scalar_from_hex(stored)
        self.assertEqual(x25519_pure.public_key_from_scalar(restored), pub)

    def test_esp32_login_proof_matches_backend_verifier(self):
        """Server ephemeral + device identity ECDH, then HMAC over the UART transcript."""
        device_scalar = x25519_pure.clamp_scalar(os.urandom(32))
        device_pub = x25519_pure.public_key_from_scalar(device_scalar)
        server_scalar = x25519_pure.clamp_scalar(os.urandom(32))
        server_pub = x25519_pure.public_key_from_scalar(server_scalar)

        shared_device = x25519_pure.shared_secret(device_scalar, server_pub)
        shared_server = x25519_pure.shared_secret(
            x25519_pure.scalar_from_hex(x25519_pure.scalar_to_hex(server_scalar)),
            device_pub,
        )
        self.assertEqual(shared_device, shared_server)

        login_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        customer_id = "11111111-2222-3333-4444-555555555555"
        nonce = os.urandom(16)
        proof = esp32_mfa_bridge._compute_login_proof(shared_device, login_id, customer_id, nonce)
        esp32_mfa_bridge._verify_login_proof(shared_server, login_id, customer_id, nonce, proof)
        self.assertEqual(len(proof.hex()), 64)
        self.assertEqual(len(nonce.hex()), 32)

    def test_hmac_matches_transcript_bytes(self):
        key = os.urandom(32)
        nonce = os.urandom(16)
        std = esp32_mfa_bridge._compute_login_proof(key, "login", "cust", nonce)
        transcript = b"esp32c6-mfa-login-proof-v1|login|cust|" + nonce
        import hashlib
        import hmac

        self.assertEqual(hmac.new(key, transcript, hashlib.sha256).digest(), std)


class TestProtocolParsing(unittest.TestCase):
    def test_parse_status(self):
        status = esp32_mfa_bridge._parse_status("MFA:STATUS:OK:mfa_enrolled")
        self.assertEqual(status, "mfa_enrolled")

    def test_parse_enroll_response(self):
        line = "MFA:ENROLL:OK:user-123:" + "ab" * 32
        customer, pubkey = esp32_mfa_bridge._parse_enroll_response(line)
        self.assertEqual(customer, "user-123")
        self.assertEqual(len(pubkey), 64)

    def test_parse_proof_response(self):
        proof_hex = "cd" * 32
        proof = esp32_mfa_bridge._parse_proof_response(f"MFA:PROOF:OK:{proof_hex}")
        self.assertEqual(proof, bytes.fromhex(proof_hex))

    def test_verify_login_proof_roundtrip(self):
        login_id = "LOGIN-deadbeef"
        customer_id = "cust-uuid"
        nonce = os.urandom(16)
        shared = os.urandom(32)
        proof = esp32_mfa_bridge._compute_login_proof(shared, login_id, customer_id, nonce)
        esp32_mfa_bridge._verify_login_proof(shared, login_id, customer_id, nonce, proof)

    def test_verify_login_proof_rejects_bad_proof(self):
        with self.assertRaises(ValueError):
            esp32_mfa_bridge._verify_login_proof(
                os.urandom(32),
                "LOGIN-x",
                "cust",
                os.urandom(16),
                b"\x00" * 32,
            )


class TestBridgeWithMockSerial(unittest.TestCase):
    def test_device_status_mock(self):
        mock_ser = MagicMock()
        mock_ser.in_waiting = 0
        mock_ser.read.side_effect = [
            b"MFA:STATUS:OK:puf_ready\n",
        ]

        with patch.object(esp32_mfa_bridge, "_open_port", return_value=mock_ser):
            status = esp32_mfa_bridge.device_status("COM99")
        self.assertEqual(status, "puf_ready")
        mock_ser.close.assert_called_once()

    def test_enroll_device_mock(self):
        pubkey = "aa" * 32
        mock_ser = MagicMock()
        mock_ser.in_waiting = 0
        mock_ser.read.side_effect = [
            b"MFA:STATUS:OK:puf_ready\n",
            f"MFA:ENROLL:OK:test-user:{pubkey}\n".encode(),
        ]

        with patch.object(esp32_mfa_bridge, "_open_port", return_value=mock_ser):
            result = esp32_mfa_bridge.enroll_device("COM99", "test-user")
        self.assertEqual(result, pubkey)


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestX25519Pure))
    suite.addTests(loader.loadTestsFromTestCase(TestProtocolParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestBridgeWithMockSerial))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
