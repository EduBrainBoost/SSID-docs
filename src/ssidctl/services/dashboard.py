"""Mission Control dashboard — loopback-only Flask UI.

Exposes Board, Calendar, Content, Memory modules as read-only
server-rendered views. Binds to 127.0.0.1 only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ssidctl.config import EMSConfig


class DashboardError(Exception):
    pass


def create_dashboard_app(config: EMSConfig) -> Any:
    """Create the Mission Control Flask application.

    Args:
        config: EMS configuration with paths to state/modules.

    Returns:
        Flask app instance.

    Raises:
        DashboardError: If Flask is not installed.
    """
    try:
        from flask import Flask, render_template
    except ImportError as err:
        raise DashboardError(
            "flask not installed. Install with: pip install ssidctl[web]"
        ) from err

    template_dir = Path(__file__).parent / "templates"
    app = Flask(__name__, template_folder=str(template_dir))

    # --- Board Blueprint ---
    from flask import Blueprint

    board_bp = Blueprint("board", __name__, url_prefix="/board")

    @board_bp.route("/")
    def board_list() -> str:
        from ssidctl.modules.board import Board

        board = Board(config.paths.state_dir / "board")
        tasks = board.list_tasks()
        statuses = ["BACKLOG", "READY", "DOING", "BLOCKED", "REVIEW", "DONE", "CANCELLED"]
        grouped = {s: [t for t in tasks if t["status"] == s] for s in statuses}
        return render_template("board.html", grouped=grouped, statuses=statuses, total=len(tasks))

    @board_bp.route("/<task_id>")
    def board_detail(task_id: str) -> str | tuple[str, int]:
        from ssidctl.modules.board import Board, BoardError

        board = Board(config.paths.state_dir / "board")
        try:
            task = board.show(task_id)
        except BoardError:
            return render_template("error.html", message=f"Task not found: {task_id}"), 404
        return render_template("board_detail.html", task=task)

    # --- Calendar Blueprint ---
    calendar_bp = Blueprint("calendar", __name__, url_prefix="/calendar")

    @calendar_bp.route("/")
    def calendar_list() -> str:
        from ssidctl.modules.calendar_mod import Calendar

        cal = Calendar(config.paths.state_dir / "calendar")
        jobs = cal.list_jobs()
        return render_template("calendar.html", jobs=jobs)

    # --- Content Blueprint ---
    content_bp = Blueprint("content", __name__, url_prefix="/content")

    @content_bp.route("/")
    def content_list() -> str:
        from ssidctl.modules.content import ContentPipeline

        pipeline = ContentPipeline(config.paths.state_dir / "content")
        items = pipeline.list_items()
        stages = [
            "IDEA",
            "OUTLINE",
            "BRIEF",
            "SCRIPT",
            "ASSETS",
            "REVIEW",
            "PUBLISH",
            "ARCHIVE",
            "POSTMORTEM",
        ]
        return render_template("content.html", items=items, stages=stages)

    @content_bp.route("/<content_id>")
    def content_detail(content_id: str) -> str | tuple[str, int]:
        from ssidctl.modules.content import ContentError, ContentPipeline

        pipeline = ContentPipeline(config.paths.state_dir / "content")
        try:
            item = pipeline.show(content_id)
        except ContentError:
            return render_template("error.html", message=f"Content not found: {content_id}"), 404
        return render_template("content_detail.html", item=item)

    # --- Memory Blueprint ---
    memory_bp = Blueprint("memory", __name__, url_prefix="/memory")

    @memory_bp.route("/")
    def memory_list() -> str:
        from ssidctl.modules.memory import MemoryVault

        vault = MemoryVault(config.paths.state_dir / "memory")
        docs = vault.list_docs()
        # Strip internal paths — only metadata for display
        for d in docs:
            d.pop("path", None)
        return render_template("memory.html", docs=docs)

    @memory_bp.route("/<doc_id>")
    def memory_detail(doc_id: str) -> str | tuple[str, int]:
        from ssidctl.modules.memory import MemoryError as MemError
        from ssidctl.modules.memory import MemoryVault

        vault = MemoryVault(config.paths.state_dir / "memory")
        try:
            doc = vault.show(doc_id)
        except MemError:
            return render_template("error.html", message=f"Document not found: {doc_id}"), 404
        # Strip raw content — hash-only policy
        doc.pop("content", None)
        doc.pop("path", None)
        return render_template("memory_detail.html", doc=doc)

    # --- Index route ---
    @app.route("/")
    def index() -> str:
        from ssidctl.modules.board import Board
        from ssidctl.modules.calendar_mod import Calendar
        from ssidctl.modules.content import ContentPipeline
        from ssidctl.modules.memory import MemoryVault

        board = Board(config.paths.state_dir / "board")
        cal = Calendar(config.paths.state_dir / "calendar")
        pipeline = ContentPipeline(config.paths.state_dir / "content")
        vault = MemoryVault(config.paths.state_dir / "memory")

        summary = {
            "tasks": len(board.list_tasks()),
            "tasks_doing": len(board.list_tasks(status="DOING")),
            "jobs": len(cal.list_jobs()),
            "content": len(pipeline.list_items()),
            "memory": len(vault.list_docs()),
        }
        return render_template("index.html", summary=summary)

    @app.route("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    # Register blueprints
    app.register_blueprint(board_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(memory_bp)

    return app
