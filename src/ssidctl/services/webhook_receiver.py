"""GitHub App Webhook Receiver — repo-connector scaffold.

Receives GitHub webhook events (push, pull_request, check_suite),
verifies HMAC-SHA256 signatures, dispatches to ssidctl commands.
Requires: flask (optional dependency).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class WebhookError(Exception):
    pass


@dataclass
class WebhookReceiver:
    """Processes GitHub webhook events with signature verification."""

    secret: str
    dispatch_fn: Callable[[str, dict[str, Any]], Any] | None = None
    _handlers: dict[str, Callable[..., dict[str, Any]]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._handlers = {
            "push": self._handle_push,
            "pull_request": self._handle_pull_request,
            "check_suite": self._handle_check_suite,
            "check_run": self._handle_check_run,
        }

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature."""
        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    def handle_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch event to appropriate handler."""
        handler = self._handlers.get(event_type)
        if handler is None:
            return {"status": "ignored", "event": event_type}
        result = handler(payload)
        if self.dispatch_fn:
            self.dispatch_fn(event_type, payload)
        return result

    def _handle_push(self, payload: dict[str, Any]) -> dict[str, Any]:
        ref = payload.get("ref", "")
        commits = payload.get("commits", [])
        return {
            "status": "received",
            "event": "push",
            "ref": ref,
            "commit_count": len(commits),
        }

    def _handle_pull_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        return {
            "status": "received",
            "event": "pull_request",
            "action": action,
            "pr_number": pr.get("number"),
            "head_sha": pr.get("head", {}).get("sha"),
        }

    def _handle_check_suite(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action", "")
        suite = payload.get("check_suite", {})
        return {
            "status": "received",
            "event": "check_suite",
            "action": action,
            "head_sha": suite.get("head_sha"),
        }

    def _handle_check_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action", "")
        check = payload.get("check_run", {})
        return {
            "status": "received",
            "event": "check_run",
            "action": action,
            "name": check.get("name"),
            "conclusion": check.get("conclusion"),
        }

    def create_check_run(
        self,
        repo: str,
        head_sha: str,
        name: str,
        status: str = "completed",
        conclusion: str | None = "success",
    ) -> dict[str, Any]:
        """Create a GitHub Check Run via gh CLI."""
        body = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
        }
        if conclusion and status == "completed":
            body["conclusion"] = conclusion
        try:
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repo}/check-runs",
                    "--method",
                    "POST",
                    "--input",
                    "-",
                ],
                input=json.dumps(body),
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "status": "created" if result.returncode == 0 else "error",
                "exit_code": result.returncode,
                "output": result.stdout[:200],
            }
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            return {"status": "error", "error": str(exc)}


def create_app(receiver: WebhookReceiver) -> Any:
    """Create a Flask app for webhook handling."""
    try:
        from flask import Flask, jsonify, request
    except ImportError as err:
        raise WebhookError("flask not installed. Install with: pip install flask") from err

    app = Flask(__name__)

    @app.route("/webhook", methods=["POST"])
    def webhook() -> Any:
        signature = request.headers.get("X-Hub-Signature-256", "")
        if not receiver.verify_signature(request.data, signature):
            return jsonify({"error": "Invalid signature"}), 401
        event_type = request.headers.get("X-GitHub-Event", "ping")
        payload = request.get_json(force=True)
        result = receiver.handle_event(event_type, payload)
        return jsonify(result), 200

    @app.route("/health", methods=["GET"])
    def health() -> Any:
        return jsonify({"status": "ok"}), 200

    return app
