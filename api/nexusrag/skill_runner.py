from __future__ import annotations

from typing import Any

from nexusrag import providers
from nexusrag.answerer import NO_RESULTS, Answerer
from nexusrag.providers import ProviderConfig
from nexusrag.skills import Skill
from nexusrag.sources import SourceStore

OVERVIEW_SOURCES = 12
OVERVIEW_CHARS = 700
PRIMARY_CHARS = 3000
REFERENCE_HITS = 3
TOPIC_HITS = 6

GROUNDING = "Cite passages like [1]. Use only the passages. If they do not contain what is needed, say so."


class SkillRunner:
    """Runs a Skill over a Scope. Every passage comes from ids the scope resolver
    allowed, so a Skill cannot see a Private Source."""

    def __init__(self, store: SourceStore, answerer: Answerer) -> None:
        self.store = store
        self.answerer = answerer

    # ---- passage gathering
    def _excerpt(self, source_id: str, chars: int) -> dict[str, Any] | None:
        row = self.store.raw(source_id)
        if row is None or not row["extracted_text"].strip():
            return None
        return {"source_id": source_id, "position": {}, "text": row["extracted_text"].strip()[:chars]}

    def _overview(self, ids: set[str]) -> list[dict[str, Any]]:
        ordered = [s["id"] for s in self.store.list() if s["id"] in ids]
        passages = [self._excerpt(i, OVERVIEW_CHARS) for i in ordered[:OVERVIEW_SOURCES]]
        return [p for p in passages if p]

    def _named_source(self, arg: str, ids: set[str]) -> str | None:
        wanted = arg.strip().lower()
        if not wanted:
            return None
        named = [(s["id"], s["name"].lower()) for s in self.store.list() if s["id"] in ids]
        for sid, name in named:
            if name == wanted:
                return sid
        for sid, name in named:
            if wanted in name:
                return sid
        return None

    def passages_for(self, name: str, arg: str, ids: set[str]) -> tuple[list[dict[str, Any]], str | None]:
        """(passages, primary_source_id). Order matters: the first passage leads."""
        if not arg:
            return self._overview(ids), None
        primary = self._named_source(arg, ids)
        if primary:
            lead = self._excerpt(primary, PRIMARY_CHARS)
            others = self.answerer.retrieve(arg, ids - {primary})[:REFERENCE_HITS]
            return ([lead] if lead else []) + others, primary
        return self.answerer.retrieve(arg, ids)[:TOPIC_HITS], None

    # ---- run
    def run(self, skill: Skill, arg: str, ids: set[str], config: ProviderConfig | None) -> dict[str, Any]:
        passages, primary = self.passages_for(skill.name, arg, ids)
        if not passages:
            return {"answer": NO_RESULTS, "citations": [], "mode": "no_results", "skill": skill.name}
        citations = self.answerer._citations(passages)
        if config is None:
            return {
                "answer": _extractive(passages, citations),
                "citations": citations,
                "mode": "extractive",
                "skill": skill.name,
            }
        blocks = "\n\n".join(
            f"[{c['n']}] {c['source_name']}{' (primary Source)' if p['source_id'] == primary else ''}\n{p['text']}"
            for c, p in zip(citations, passages)
        )
        request = arg or "the whole Scope"
        content = f"Request: {request}\n\nPassages:\n{blocks}"
        text = providers.complete(config, f"{skill.instruction}\n\n{GROUNDING}", content, max_tokens=900)
        return {"answer": text, "citations": citations, "mode": "model", "skill": skill.name}


def _extractive(passages: list[dict[str, Any]], citations: list[dict[str, Any]]) -> str:
    lines = ["From your Sources:"]
    for p, c in zip(passages, citations):
        body = " ".join(p["text"].split())
        lines.append(f"- {c['source_name']}: {body[:200]}{'…' if len(body) > 200 else ''} [{c['n']}]")
    return "\n".join(lines)
