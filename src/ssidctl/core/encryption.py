"""Encryption at Rest — Fernet-based envelope encryption for EMS data.

Encrypts evidence, state, and configuration files at rest.
Uses Python cryptography library (Fernet symmetric encryption).
Key derivation from password via PBKDF2 or direct key loading.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_file

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


class EncryptionError(Exception):
    pass


def _require_crypto() -> None:
    if not _HAS_CRYPTO:
        raise EncryptionError(
            "cryptography package not installed. Install with: pip install cryptography"
        )


@dataclass
class EncryptionConfig:
    """Encryption configuration."""

    key_path: Path | None = None
    password: str | None = None
    enabled: bool = True


def generate_key() -> bytes:
    """Generate a new Fernet encryption key."""
    _require_crypto()
    return Fernet.generate_key()


def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive a Fernet key from a password using PBKDF2.

    Returns (key, salt) tuple. Store the salt alongside encrypted data.
    """
    _require_crypto()
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


class EncryptionManager:
    """Manages encryption/decryption of files and data."""

    def __init__(self, config: EncryptionConfig) -> None:
        self._config = config
        self._fernet: Any = None
        if config.enabled:
            self._init_fernet()

    def _init_fernet(self) -> None:
        _require_crypto()
        if self._config.key_path and self._config.key_path.exists():
            key = self._config.key_path.read_bytes().strip()
        elif self._config.password:
            salt_path = self._config.key_path.parent / ".salt" if self._config.key_path else None
            salt = None
            if salt_path and salt_path.exists():
                salt = salt_path.read_bytes()
            key, new_salt = derive_key(self._config.password, salt)
            if salt_path and salt is None:
                salt_path.parent.mkdir(parents=True, exist_ok=True)
                salt_path.write_bytes(new_salt)
        else:
            raise EncryptionError("Either key_path or password must be provided")
        self._fernet = Fernet(key)

    @property
    def enabled(self) -> bool:
        return self._config.enabled and self._fernet is not None

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt raw bytes, returns Fernet token."""
        if not self.enabled:
            return data
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt a Fernet token back to plaintext bytes."""
        if not self.enabled:
            return token
        try:
            return self._fernet.decrypt(token)
        except Exception as exc:
            raise EncryptionError(f"Decryption failed: {exc}") from exc

    def encrypt_file(self, source: Path, dest: Path | None = None) -> Path:
        """Encrypt a file. If dest is None, encrypts in-place with .enc suffix."""
        if not self.enabled:
            return source
        plaintext = source.read_bytes()
        ciphertext = self.encrypt(plaintext)
        out = dest or source.with_suffix(source.suffix + ".enc")
        out.write_bytes(ciphertext)
        return out

    def decrypt_file(self, source: Path, dest: Path | None = None) -> Path:
        """Decrypt a .enc file. If dest is None, strips .enc suffix."""
        if not self.enabled:
            return source
        ciphertext = source.read_bytes()
        plaintext = self.decrypt(ciphertext)
        if dest is None:
            name = source.name
            if name.endswith(".enc"):
                name = name[:-4]
            dest = source.parent / name
        dest.write_bytes(plaintext)
        return dest

    def encrypt_json(self, data: dict[str, Any]) -> bytes:
        """Encrypt a JSON-serializable dict."""
        plaintext = json.dumps(data, separators=(",", ":")).encode()
        return self.encrypt(plaintext)

    def decrypt_json(self, token: bytes) -> dict[str, Any]:
        """Decrypt a Fernet token to a dict."""
        plaintext = self.decrypt(token)
        return json.loads(plaintext)

    @staticmethod
    def file_hash(path: Path) -> str:
        """SHA-256 hash of a file (works on both encrypted and plaintext)."""
        return sha256_file(path)
