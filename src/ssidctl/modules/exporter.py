"""Content exporter — Markdown, JSON formats."""

from __future__ import annotations

import json
from typing import Any

from ssidctl.modules.content import ContentPipeline


class ContentExporter:
    def __init__(self, pipeline: ContentPipeline) -> None:
        self._pipeline = pipeline

    def to_markdown(self, content_id: str) -> str:
        item = self._pipeline.show(content_id)
        lines = [
            f"# {item['title']}",
            "",
            f"**Stage:** {item['stage']}",
            f"**Channel:** {item.get('channel', '-')}",
            f"**Owner:** {item.get('owner', '-')}",
            f"**Tags:** {', '.join(item.get('tags', []))}",
            f"**Created:** {item.get('created_utc', '-')}",
            "",
        ]
        if item.get("publish_date"):
            lines.append(f"**Publish Date:** {item['publish_date']}")
            lines.append("")
        if item.get("checklist"):
            lines.append("## Review Checklist")
            for check in item["checklist"]:
                lines.append(f"- [ ] {check}")
            lines.append("")
        if item.get("attachments"):
            lines.append("## Attachments")
            for att in item["attachments"]:
                lines.append(
                    f"- {att.get('path', '?')} ({att.get('mime', '?')})"
                    f" `{att.get('hash', '')[:20]}...`"
                )
            lines.append("")
        return "\n".join(lines)

    def to_json(self, content_id: str) -> dict[str, Any]:
        return self._pipeline.show(content_id)

    def to_file(self, content_id: str, output_path: str, fmt: str = "md") -> str:
        from pathlib import Path

        p = Path(output_path)
        if fmt == "md":
            p.write_text(self.to_markdown(content_id), encoding="utf-8")
        elif fmt == "json":
            p.write_text(
                json.dumps(self.to_json(content_id), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        else:
            raise ValueError(f"Unsupported format: {fmt}")
        return str(p)
