"""Workflow definitions package for SSID-EMS durable workflow engine.

Each module in this package exports a builder function that constructs
and registers a :class:`~ssidctl.workflow.registry.WorkflowDefinition`
with the global registry.

Available workflow definitions:
- ``drift_sentinel_v1``: 9-step drift detection and optional remediation workflow.
"""
