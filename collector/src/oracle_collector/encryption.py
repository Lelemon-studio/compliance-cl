from __future__ import annotations

import base64
import json
import os
from typing import Any


def load_key(path: str) -> bytes:
    raw = open(path, "rb").read().strip()  # noqa: SIM115 - immediately consumed
    try:
        key = base64.b64decode(raw, validate=True)
    except ValueError:
        key = raw
    if len(key) != 32:
        raise ValueError("AES-256-GCM key must be exactly 32 bytes (raw or base64 encoded)")
    return key


def encrypt_payload(payload: dict[str, Any], key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError("AES-256-GCM requires a 32-byte key")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:  # pragma: no cover - depends on optional installation
        raise RuntimeError("install the encryption extra to use AES-256-GCM") from exc
    nonce = os.urandom(12)
    plaintext = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, b"oracle-compliance-collector:v1")
    envelope = {
        "algorithm": "AES-256-GCM",
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, sort_keys=True).encode("utf-8")

