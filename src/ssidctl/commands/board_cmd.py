"""ssidctl board — Task Board (Kanban) commands."""

from __future__ import annotations

import argparse
import sys

from ssidctl.config import EMSConfig
from ssidctl.modules.board import Board, BoardError


def register(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("board", help="Task Board (Kanban)")
    sub = parser.add_subparsers(dest="board_action")

    add_p = sub.add_parser("add", help="Add a task")
    add_p.add_argument("task_id", type=str)
    add_p.add_argument("title", type=str)
    add_p.add_argument("--module", type=str, default="EMS")
    add_p.add_argument("--owner", type=str, default="user")
    add_p.add_argument("--priority", type=str, default="P1")
    add_p.add_argument("--deadline", type=str, default=None, help="Deadline UTC (ISO8601)")

    move_p = sub.add_parser("move", help="Move a task to a new status")
    move_p.add_argument("task_id", type=str)
    move_p.add_argument("status", type=str)

    assign_p = sub.add_parser("assign", help="Assign a task")
    assign_p.add_argument("task_id", type=str)
    assign_p.add_argument("owner", type=str)

    sub.add_parser("list", help="List tasks")
    show_p = sub.add_parser("show", help="Show task details")
    show_p.add_argument("task_id", type=str)

    update_p = sub.add_parser("update", help="Update task fields")
    update_p.add_argument("task_id", type=str)
    update_p.add_argument("--title", type=str, default=None)
    update_p.add_argument("--priority", type=str, default=None)
    update_p.add_argument("--module", type=str, default=None)
    update_p.add_argument("--deadline", type=str, default=None, help="Deadline UTC (ISO8601)")

    delete_p = sub.add_parser("delete", help="Delete a task")
    delete_p.add_argument("task_id", type=str)

    parser.set_defaults(func=cmd_board)


def cmd_board(args: argparse.Namespace, config: EMSConfig) -> int:
    board = Board(config.paths.state_dir / "board")

    try:
        if args.board_action == "add":
            task = board.add(
                args.task_id,
                args.title,
                args.module,
                args.owner,
                args.priority,
                deadline=args.deadline,
            )
            print(f"Added: {task['task_id']} [{task['status']}] {task['title']}")
        elif args.board_action == "move":
            task = board.move(args.task_id, args.status)
            print(f"Moved: {task['task_id']} -> {task['status']}")
        elif args.board_action == "assign":
            task = board.assign(args.task_id, args.owner)
            print(f"Assigned: {task['task_id']} -> {task['owner']}")
        elif args.board_action == "list":
            tasks = board.list_tasks()
            if not tasks:
                print("No tasks.")
                return 0
            for t in tasks:
                s, p, tid = t["status"], t["priority"], t["task_id"]
                print(f"  [{s:9s}] {p} {tid}: {t['title']} ({t['owner']})")
        elif args.board_action == "show":
            task = board.show(args.task_id)
            for k, v in task.items():
                print(f"  {k}: {v}")
        elif args.board_action == "update":
            task = board.update(
                args.task_id,
                title=args.title,
                priority=args.priority,
                module=args.module,
                deadline=args.deadline,
            )
            print(f"Updated: {task['task_id']} [{task['priority']}] {task['title']}")
        elif args.board_action == "delete":
            task = board.delete(args.task_id)
            print(f"Deleted: {task['task_id']} {task['title']}")
        else:
            print(
                "Usage: ssidctl board {add|move|assign|list|show|update|delete}",
                file=sys.stderr,
            )
            return 1
    except BoardError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0
