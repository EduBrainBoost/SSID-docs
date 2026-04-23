"""Workflow definition registry with fixed step-type allowlist.

All step types must be declared in STEP_TYPE_ALLOWLIST.  Any workflow
definition referencing an unlisted step type is rejected at registration time
(fail-closed / anti-gaming).  No wildcards, no regex — exact-string membership
only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------

StepFunction = Callable[[dict[str, Any]], dict[str, Any]]

# ---------------------------------------------------------------------------
# Fixed allowlist — exactly 9 types, no wildcards, no regex (ROOT-24-LOCK /
# Anti-Gaming).  To add a new type an explicit code change + PR is required.
# ---------------------------------------------------------------------------

STEP_TYPE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "collect_state_snapshot",
        "compute_drift",
        "classify_drift",
        "emit_evidence",
        "propose_remediation",
        "await_operator_decision",
        "execute_remediation",
        "post_verify",
        "close_run",
    }
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class RegistryError(Exception):
    """Raised when a registry operation fails (e.g. unknown step type, missing
    workflow, or duplicate registration)."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StepDefinition:
    """Describes a single step within a workflow.

    Attributes:
        step_type: Must be a member of ``STEP_TYPE_ALLOWLIST``.
        function: Callable that receives a ``dict[str, Any]`` context and
            returns a ``dict[str, Any]`` result.
        retryable: Whether failed invocations may be retried.
        max_attempts: Maximum total attempts (including first).  Only
            meaningful when ``retryable`` is ``True``.
        requires_approval: When ``True`` the step must not execute until an
            operator has explicitly approved it (e.g. ``await_operator_decision``
            and ``execute_remediation`` steps).
    """

    step_type: str
    function: StepFunction
    retryable: bool = True
    max_attempts: int = 3
    requires_approval: bool = False


@dataclass
class WorkflowDefinition:
    """Describes a complete, named workflow composed of ordered steps.

    Attributes:
        name: Unique workflow name used as the registry key.
        version: Semver-style version string for the definition.
        steps: Ordered list of :class:`StepDefinition` objects.
    """

    name: str
    version: str
    steps: list[StepDefinition] = field(default_factory=list)

    def add_step(self, step: StepDefinition) -> None:
        """Append *step* to the workflow's step list.

        Args:
            step: A :class:`StepDefinition` to append.
        """
        self.steps.append(step)


# ---------------------------------------------------------------------------
# Global registry (module-level singleton)
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, WorkflowDefinition] = {}


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------


def register_workflow(definition: WorkflowDefinition) -> None:
    """Register *definition* after validating all step types.

    Validation rules (fail-closed):
    - Every ``step.step_type`` in *definition.steps* must appear verbatim in
      ``STEP_TYPE_ALLOWLIST``.  Unknown types cause an immediate
      :class:`RegistryError` — no partial registration.
    - ``await_operator_decision`` steps must have ``requires_approval=True``.

    Args:
        definition: The :class:`WorkflowDefinition` to register.

    Raises:
        RegistryError: If any step type is not in the allowlist, or if an
            ``await_operator_decision`` step has ``requires_approval=False``.
    """
    for step in definition.steps:
        if step.step_type not in STEP_TYPE_ALLOWLIST:
            raise RegistryError(
                f"Workflow '{definition.name}': unknown step_type "
                f"'{step.step_type}'. Allowed types: {sorted(STEP_TYPE_ALLOWLIST)}"
            )
        # Approval gate enforcement: await_operator_decision MUST require approval.
        if step.step_type == "await_operator_decision" and not step.requires_approval:
            raise RegistryError(
                f"Workflow '{definition.name}': step_type "
                "'await_operator_decision' must have requires_approval=True"
            )

    _REGISTRY[definition.name] = definition


def get_workflow(name: str) -> WorkflowDefinition:
    """Return the registered :class:`WorkflowDefinition` for *name*.

    Args:
        name: Workflow name as supplied to :func:`register_workflow`.

    Returns:
        The matching :class:`WorkflowDefinition`.

    Raises:
        RegistryError: If *name* is not found in the registry.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        raise RegistryError(
            f"Workflow '{name}' is not registered. Available: {sorted(_REGISTRY.keys())}"
        ) from None


def list_workflows() -> list[str]:
    """Return a sorted list of all registered workflow names.

    Returns:
        A new sorted list of workflow name strings.
    """
    return sorted(_REGISTRY.keys())


def clear_registry() -> None:
    """Remove all entries from the registry.

    FOR TESTING ONLY.  Do not call from production code paths.
    """
    _REGISTRY.clear()
