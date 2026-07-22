"""Build-time encryption of the analytics payload.

The payload is gzipped, then encrypted with AES-256-GCM using a key derived
from the passphrase via PBKDF2-SHA256 (250k iterations). The browser decrypts
with the Web Crypto API — the plaintext never ships in the static site.
"""

from __future__ import annotations

import base64
import gzip
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

PBKDF2_ITERATIONS = 250_000


def encrypt_payload(data: dict[str, Any], passphrase: str) -> dict[str, str]:
    """Encrypt a JSON-serializable dict; returns base64 fields for the client."""
    plaintext = gzip.compress(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        compresslevel=9,
    )
    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=PBKDF2_ITERATIONS)
    key = kdf.derive(passphrase.encode("utf-8"))
    ciphertext = AESGCM(key).encrypt(iv, plaintext, None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {
        "salt": b64(salt),
        "iv": b64(iv),
        "iterations": str(PBKDF2_ITERATIONS),
        "ciphertext": b64(ciphertext),
    }
