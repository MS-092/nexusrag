"""Skills: preset instructions the user calls from chat as /name.

A Skill is one Markdown file in the skills folder:

    ---
    name: summarize
    description: One line shown in the Skill list.
    usage: /summarize [source name or topic]
    ---
    The instruction text, sent to the model as its system prompt.

Dropping a new file in adds a new command. No code, no restart.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INVOCATION = re.compile(r"^/([A-Za-z][A-Za-z0-9_-]*)(?:\s+(.*))?$", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    usage: str
    instruction: str


def parse_skill(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip().lower()] = value.strip()
            body = parts[2].strip()
    name = (meta.get("name") or path.stem).strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or not body:
        return None
    return Skill(
        name=name,
        description=meta.get("description", ""),
        usage=meta.get("usage") or f"/{name}",
        instruction=body,
    )


def load_skills(directory: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.md")):
            skill = parse_skill(path)
            if skill:
                skills[skill.name] = skill
    return skills


def parse_invocation(text: str) -> tuple[str, str] | None:
    """('summarize', 'finance.pdf') for '/summarize finance.pdf'. None for ordinary questions."""
    match = INVOCATION.match(text.strip())
    if not match:
        return None
    return match.group(1).lower(), (match.group(2) or "").strip()
