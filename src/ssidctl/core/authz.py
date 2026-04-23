"""Role-Based Access Control (RBAC) for SSID EMS.

Defines 5 roles with a permission matrix enforcing least-privilege.
Roles: OWNER, ADMIN, REVIEWER, CONTRIBUTOR, READONLY.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AuthzError(Exception):
    pass


class Role(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    CONTRIBUTOR = "contributor"
    READONLY = "readonly"


class Permission(Enum):
    # Evidence
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_WRITE = "evidence:write"
    EVIDENCE_SEAL = "evidence:seal"
    # Gates
    GATE_RUN = "gate:run"
    GATE_OVERRIDE = "gate:override"
    # Lifecycle
    LIFECYCLE_APPROVE = "lifecycle:approve"
    LIFECYCLE_TRANSITION = "lifecycle:transition"
    # Configuration
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    # PR / Merge
    PR_CREATE = "pr:create"
    PR_MERGE = "pr:merge"
    # Admin
    ADMIN_QUARANTINE = "admin:quarantine"
    ADMIN_LOCK = "admin:lock"
    ADMIN_INCIDENT = "admin:incident"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: set(Permission),
    Role.ADMIN: {
        Permission.EVIDENCE_READ,
        Permission.EVIDENCE_WRITE,
        Permission.EVIDENCE_SEAL,
        Permission.GATE_RUN,
        Permission.GATE_OVERRIDE,
        Permission.LIFECYCLE_APPROVE,
        Permission.LIFECYCLE_TRANSITION,
        Permission.CONFIG_READ,
        Permission.CONFIG_WRITE,
        Permission.PR_CREATE,
        Permission.PR_MERGE,
        Permission.ADMIN_QUARANTINE,
        Permission.ADMIN_LOCK,
        Permission.ADMIN_INCIDENT,
    },
    Role.REVIEWER: {
        Permission.EVIDENCE_READ,
        Permission.GATE_RUN,
        Permission.LIFECYCLE_APPROVE,
        Permission.CONFIG_READ,
        Permission.PR_CREATE,
    },
    Role.CONTRIBUTOR: {
        Permission.EVIDENCE_READ,
        Permission.GATE_RUN,
        Permission.LIFECYCLE_TRANSITION,
        Permission.CONFIG_READ,
        Permission.PR_CREATE,
    },
    Role.READONLY: {
        Permission.EVIDENCE_READ,
        Permission.CONFIG_READ,
    },
}


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def check_permission(role: Role, permission: Permission) -> None:
    """Raise AuthzError if role lacks permission."""
    if not has_permission(role, permission):
        raise AuthzError(f"Role '{role.value}' lacks permission '{permission.value}'")


@dataclass
class Identity:
    """Represents an authenticated user with a role."""

    username: str
    role: Role

    def can(self, permission: Permission) -> bool:
        return has_permission(self.role, permission)

    def require(self, permission: Permission) -> None:
        check_permission(self.role, permission)


def resolve_role(role_name: str) -> Role:
    """Resolve a role name string to a Role enum value."""
    try:
        return Role(role_name.lower())
    except ValueError as err:
        valid = ", ".join(r.value for r in Role)
        raise AuthzError(f"Unknown role '{role_name}'. Valid roles: {valid}") from err
