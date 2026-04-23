"""OIDC/OAuth2 Authentication — identity verification scaffold.

Verifies JWT tokens from OIDC providers (GitHub, Azure AD, Keycloak).
Extracts identity claims for RBAC integration.
Requires: PyJWT (optional dependency).
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import jwt as pyjwt

    _HAS_JWT = True
except ImportError:
    _HAS_JWT = False


class OIDCError(Exception):
    pass


def _require_jwt() -> None:
    if not _HAS_JWT:
        raise OIDCError("PyJWT not installed. Install with: pip install PyJWT[crypto]")


@dataclass
class OIDCConfig:
    """OIDC provider configuration."""

    issuer: str
    client_id: str
    audience: str | None = None
    jwks_uri: str | None = None
    algorithms: list[str] | None = None

    def __post_init__(self) -> None:
        if self.algorithms is None:
            self.algorithms = ["RS256"]
        if self.jwks_uri is None:
            self.jwks_uri = f"{self.issuer.rstrip('/')}/.well-known/jwks.json"


class OIDCAuthenticator:
    """Verifies JWT tokens and extracts identity claims."""

    def __init__(self, config: OIDCConfig) -> None:
        self._config = config
        self._jwks: dict[str, Any] | None = None

    def _fetch_jwks(self) -> dict[str, Any]:
        """Fetch JSON Web Key Set from the OIDC provider."""
        if self._jwks is not None:
            return self._jwks
        try:
            req = urllib.request.Request(  # noqa: S310
                self._config.jwks_uri or "",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                self._jwks = json.loads(resp.read())
            return self._jwks or {}
        except Exception as exc:
            raise OIDCError(f"Failed to fetch JWKS: {exc}") from exc

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a JWT token.

        Returns the decoded claims if valid.
        Raises OIDCError on verification failure.
        """
        _require_jwt()
        try:
            jwks = self._fetch_jwks()
            jwk_client = pyjwt.PyJWKClient.__new__(pyjwt.PyJWKClient)
            # Manual JWKS loading without HTTP fetch
            jwk_client._jwks = jwks  # type: ignore[attr-defined]

            header = pyjwt.get_unverified_header(token)
            kid = header.get("kid")
            key = None
            for jwk_data in jwks.get("keys", []):
                if jwk_data.get("kid") == kid:
                    key = pyjwt.algorithms.RSAAlgorithm.from_jwk(jwk_data)
                    break

            if key is None:
                raise OIDCError(f"No matching key found for kid={kid}")

            claims = pyjwt.decode(
                token,
                key,  # type: ignore[arg-type]
                algorithms=self._config.algorithms or ["RS256"],
                audience=self._config.audience or self._config.client_id,
                issuer=self._config.issuer,
            )
            return claims
        except pyjwt.ExpiredSignatureError as err:
            raise OIDCError("Token has expired") from err
        except pyjwt.InvalidTokenError as exc:
            raise OIDCError(f"Invalid token: {exc}") from exc

    def extract_identity(self, claims: dict[str, Any]) -> dict[str, Any]:
        """Extract normalized identity from OIDC claims.

        Handles claim differences between GitHub, Azure AD, and Keycloak.
        """
        # GitHub Actions OIDC
        if "actor" in claims:
            return {
                "username": claims.get("actor", ""),
                "email": claims.get("actor", "") + "@github",
                "provider": "github",
                "roles": [],
                "sub": claims.get("sub", ""),
            }

        # Keycloak (has realm_access with roles)
        if "realm_access" in claims:
            return {
                "username": claims.get("preferred_username", claims.get("sub", "")),
                "email": claims.get("email", ""),
                "provider": "oidc",
                "roles": claims.get("realm_access", {}).get("roles", []),
                "sub": claims.get("sub", ""),
            }

        # Azure AD (has preferred_username, uses top-level roles)
        if "preferred_username" in claims:
            return {
                "username": claims.get("preferred_username", ""),
                "email": claims.get("email", claims.get("preferred_username", "")),
                "provider": "azure_ad",
                "roles": claims.get("roles", []),
                "sub": claims.get("sub", ""),
            }

        # Generic OIDC
        return {
            "username": claims.get("preferred_username", claims.get("sub", "")),
            "email": claims.get("email", ""),
            "provider": "oidc",
            "roles": [],
            "sub": claims.get("sub", ""),
        }
