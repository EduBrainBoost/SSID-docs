"""Prompt compiler — renders templates with variables, outputs hash only.

Templates live in templates/prompts/{name}.md.
Prompt text is TRANSIENT — only the hash is persisted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ssidctl.core.hashing import sha256_bytes

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates" / "prompts"


class PromptCompileError(Exception):
    pass


class CompiledPrompt:
    """A compiled prompt — text is transient, hash is persistent."""

    def __init__(self, text: str, template_name: str, variables: dict[str, Any]) -> None:
        self._text = text
        self._template_name = template_name
        self._variables = variables
        raw = text.encode("utf-8")
        self._sha256 = sha256_bytes(raw)
        self._bytes_len = len(raw)

    @property
    def text(self) -> str:
        """Transient — do NOT persist this."""
        return self._text

    @property
    def sha256(self) -> str:
        return self._sha256

    @property
    def bytes_len(self) -> int:
        return self._bytes_len

    @property
    def template_name(self) -> str:
        return self._template_name

    def to_hash_record(self) -> dict[str, Any]:
        """Return hash-only record for persistence (no raw text)."""
        return {
            "prompt_sha256": self._sha256,
            "prompt_bytes_len": self._bytes_len,
            "prompt_source": self._template_name,
        }


def compile_prompt(
    template_name: str,
    variables: dict[str, Any],
    templates_dir: Path | None = None,
) -> CompiledPrompt:
    """Compile a prompt from template + variables.

    Args:
        template_name: Template name (e.g. 'planner', 'implementer').
        variables: Dict of {{key}} -> value substitutions.
        templates_dir: Override templates directory.

    Returns:
        CompiledPrompt with text (transient) and hash (persistent).
    """
    tdir = templates_dir or _TEMPLATES_DIR
    template_path = tdir / f"{template_name}.md"

    if not template_path.exists():
        raise PromptCompileError(f"Template not found: {template_name}")

    template_text = template_path.read_text(encoding="utf-8")

    # Load base context if exists
    base_path = tdir / "_base_context.md"
    if base_path.exists():
        base_text = base_path.read_text(encoding="utf-8")
        template_text = base_text + "\n\n" + template_text

    # Simple {{variable}} substitution
    rendered = template_text
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        rendered = rendered.replace(placeholder, str(value))

    return CompiledPrompt(rendered, template_name, variables)
