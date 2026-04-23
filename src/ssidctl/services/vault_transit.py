"""HashiCorp Vault Transit — encryption-as-a-service scaffold.

Provides envelope encryption, signing, and key rotation via Vault Transit.
Requires: hvac (optional dependency).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

try:
    import hvac

    _HAS_HVAC = True
except ImportError:
    _HAS_HVAC = False


class VaultTransitError(Exception):
    pass


def _require_hvac() -> None:
    if not _HAS_HVAC:
        raise VaultTransitError("hvac not installed. Install with: pip install hvac")


@dataclass
class VaultTransitConfig:
    """Vault Transit backend configuration."""

    url: str = "http://127.0.0.1:8200"
    token: str = ""
    mount_point: str = "transit"
    key_name: str = "ssid-ems"


class VaultTransit:
    """HashiCorp Vault Transit operations."""

    def __init__(self, config: VaultTransitConfig) -> None:
        _require_hvac()
        self._config = config
        self._client = hvac.Client(url=config.url, token=config.token)
        self._mount = config.mount_point
        self._key = config.key_name

    def encrypt(self, plaintext: bytes) -> str:
        """Encrypt data using Vault Transit.

        Returns the Vault ciphertext string (vault:v1:...).
        """
        b64 = base64.b64encode(plaintext).decode()
        result = self._client.secrets.transit.encrypt_data(
            name=self._key,
            plaintext=b64,
            mount_point=self._mount,
        )
        return result["data"]["ciphertext"]

    def decrypt(self, ciphertext: str) -> bytes:
        """Decrypt a Vault Transit ciphertext string."""
        result = self._client.secrets.transit.decrypt_data(
            name=self._key,
            ciphertext=ciphertext,
            mount_point=self._mount,
        )
        return base64.b64decode(result["data"]["plaintext"])

    def sign(self, data: bytes) -> str:
        """Sign data using Vault Transit."""
        b64 = base64.b64encode(data).decode()
        result = self._client.secrets.transit.sign_data(
            name=self._key,
            hash_input=b64,
            mount_point=self._mount,
        )
        return result["data"]["signature"]

    def verify(self, data: bytes, signature: str) -> bool:
        """Verify a Vault Transit signature."""
        b64 = base64.b64encode(data).decode()
        result = self._client.secrets.transit.verify_signed_data(
            name=self._key,
            hash_input=b64,
            signature=signature,
            mount_point=self._mount,
        )
        return result["data"]["valid"]

    def rotate_key(self) -> dict[str, Any]:
        """Trigger key rotation in Vault Transit."""
        self._client.secrets.transit.rotate_key(
            name=self._key,
            mount_point=self._mount,
        )
        key_info = self._client.secrets.transit.read_key(
            name=self._key,
            mount_point=self._mount,
        )
        return {
            "key_name": self._key,
            "latest_version": key_info["data"]["latest_version"],
            "rotated": True,
        }

    def create_key(self, key_type: str = "aes256-gcm96") -> dict[str, Any]:
        """Create a new encryption key in Vault Transit."""
        self._client.secrets.transit.create_key(
            name=self._key,
            key_type=key_type,
            mount_point=self._mount,
        )
        return {"key_name": self._key, "type": key_type, "created": True}
