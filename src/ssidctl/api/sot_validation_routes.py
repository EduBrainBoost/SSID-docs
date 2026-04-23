"""SoT Validation Ingest API — Flask Blueprint for validation events.

Endpoints:
  POST /events/sot_validation                — Ingest a validation event
  GET  /api/admin/sot-validations            — List events with filter/pagination
  GET  /api/admin/sot-validations/summary    — Aggregated summary
  GET  /api/admin/sot-validations/<run_id>   — Retrieve a single event by run_id

All responses are JSON.
Error handling: 400 on invalid payload, 409 on duplicate run_id, 404 if not found.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, request

from ssidctl.config import EMSConfig
from ssidctl.services.sot_validation_service import SoTValidationService

# ---------------------------------------------------------------------------
# Blueprint factory
# ---------------------------------------------------------------------------


def create_sot_validation_blueprint(config: EMSConfig) -> Blueprint:
    """Create the SoT validation ingest API blueprint.

    Args:
        config: EMS configuration with paths to repos and state.

    Returns:
        Flask Blueprint with /events/sot_validation and /api/admin/sot-validations routes.
    """
    bp = Blueprint("sot_validation_api", __name__)

    runs_dir = config.paths.ems_repo / "runs"

    def _get_service() -> SoTValidationService:
        return SoTValidationService(runs_dir=runs_dir)

    # -------------------------------------------------------------------
    # POST /events/sot_validation
    # -------------------------------------------------------------------

    @bp.route("/events/sot_validation", methods=["POST"])
    def ingest_sot_validation() -> tuple[dict[str, Any], int]:
        """Ingest a SoT validation event.

        Expected JSON body with required fields:
            event_type, ts, run_id, source, status, summary, findings

        Response 201: {"status": "created", "run_id": "..."}
        Response 400: {"error": "..."}
        Response 409: {"error": "Duplicate run_id: ..."}
        """
        if not request.is_json:
            return {"error": "Content-Type must be application/json"}, 400

        payload = request.get_json(silent=True)
        if payload is None:
            return {"error": "Invalid or empty JSON body"}, 400

        # Validate required fields
        missing = [f for f in SoTValidationService.REQUIRED_FIELDS if f not in payload]
        if missing:
            return {
                "error": f"Missing required fields: {', '.join(missing)}",
            }, 400

        # Validate event_type value
        if payload.get("event_type") != "sot_validation":
            return {
                "error": f"event_type must be 'sot_validation', got '{payload.get('event_type')}'",
            }, 400

        service = _get_service()

        # Duplicate check
        run_id = payload["run_id"]
        if service.event_exists(run_id):
            return {"error": f"Duplicate run_id: {run_id}"}, 409

        # Persist
        service.store_event(payload)
        return {"status": "created", "run_id": run_id}, 201

    # -------------------------------------------------------------------
    # GET /api/admin/sot-validations
    # -------------------------------------------------------------------

    @bp.route("/api/admin/sot-validations", methods=["GET"])
    @bp.route("/api/admin/sot-validations/", methods=["GET"])
    def list_sot_validations() -> tuple[dict[str, Any], int]:
        """Return stored validation events with optional filters and pagination.

        Query params:
            limit         — max events per page (default 50)
            offset        — skip N events (default 0)
            decision      — filter by decision (pass/warn/fail)
            repo          — filter by repository name
            date_from     — ISO-8601 lower bound
            date_to       — ISO-8601 upper bound
            finding_class — filter to events containing this finding class

        Response 200:
            {"events": [...], "count": N, "total": M, "offset": O, "limit": L}
        """
        try:
            limit = int(request.args.get("limit", 50))
        except (ValueError, TypeError):
            limit = 50
        try:
            offset = int(request.args.get("offset", 0))
        except (ValueError, TypeError):
            offset = 0

        decision = request.args.get("decision")
        repo = request.args.get("repo")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        finding_class = request.args.get("finding_class")

        service = _get_service()
        events, total = service.list_events(
            limit=limit,
            offset=offset,
            decision=decision,
            repo=repo,
            date_from=date_from,
            date_to=date_to,
            finding_class=finding_class,
        )
        return {
            "events": events,
            "count": len(events),
            "total": total,
            "offset": offset,
            "limit": limit,
        }, 200

    # -------------------------------------------------------------------
    # GET /api/admin/sot-validations/summary
    # -------------------------------------------------------------------

    @bp.route("/api/admin/sot-validations/summary", methods=["GET"])
    def sot_validations_summary() -> tuple[dict[str, Any], int]:
        """Return aggregated summary of all validation events.

        Response 200:
            {"total_runs": N, "by_decision": {...}, "by_repo": {...},
             "latest_run_id": "...", "latest_ts": "...", "latest_decision": "..."}
        """
        service = _get_service()
        return service.summary(), 200

    # -------------------------------------------------------------------
    # GET /api/admin/sot-validations/<run_id>
    # -------------------------------------------------------------------

    @bp.route("/api/admin/sot-validations/<string:run_id>", methods=["GET"])
    def get_sot_validation(run_id: str) -> tuple[dict[str, Any], int]:
        """Return a single validation event by run_id with grouped findings.

        Response 200: event dict with _grouped_findings
        Response 404: {"error": "Validation event not found: ..."}
        """
        service = _get_service()
        event = service.get_event(run_id)
        if event is None:
            return {"error": f"Validation event not found: {run_id}"}, 404

        # Group findings by class, severity, source for drilldown
        findings = event.get("findings", [])
        by_class: dict[str, list[dict[str, Any]]] = {}
        by_severity: dict[str, list[dict[str, Any]]] = {}
        by_source: dict[str, list[dict[str, Any]]] = {}
        for f in findings:
            cls = f.get("class", "unknown")
            sev = f.get("severity", "unknown")
            src = f.get("source", "unknown")
            by_class.setdefault(cls, []).append(f)
            by_severity.setdefault(sev, []).append(f)
            by_source.setdefault(src, []).append(f)

        event["_grouped_findings"] = {
            "by_class": {k: len(v) for k, v in by_class.items()},
            "by_severity": {k: len(v) for k, v in by_severity.items()},
            "by_source": {k: len(v) for k, v in by_source.items()},
        }
        return event, 200

    return bp
