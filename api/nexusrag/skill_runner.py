from __future__ import annotations

from typing import Any

from nexusrag import providers
from nexusrag.answerer import NO_RESULTS, Answerer
from nexusrag.providers import ProviderConfig
from nexusrag.skills import Skill
from nexusrag.sources import SourceStore

STATUS_SOURCES = 8
STATUS_CHARS = 500
STATUS_ACTIVITY = 5

OVERVIEW_SOURCES = 12
OVERVIEW_CHARS = 700
PRIMARY_CHARS = 3000
REFERENCE_HITS = 3
TOPIC_HITS = 6

GROUNDING = "Cite passages like [1]. Use only the passages. If they do not contain what is needed, say so."


class SkillRunner:
    """Runs a Skill over a Scope. Every passage comes from ids the scope resolver
    allowed, so a Skill cannot see a Private Source."""

    def __init__(self, store: SourceStore, answerer: Answerer, notebooks=None, activity=None) -> None:
        self.store = store
        self.answerer = answerer
        self.notebooks = notebooks
        self.activity = activity

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
        if skill.name == "status":
            return self.status(skill, config)
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

    def status(self, skill: Skill, config: ProviderConfig | None) -> dict[str, Any]:
        """/status: always the whole Brain, never narrowed by Scope."""
        all_sources = self.store.list()
        used_model = False
        notebooks_out: list[dict[str, Any]] = []
        for nb in (self.notebooks.list() if self.notebooks else []):
            members = self.notebooks.members(nb["id"])
            shareable = [m for m in members if not m["private"] and m["state"] == "ready"]
            if config is not None and shareable:
                # Only non-private excerpts ever leave the machine.
                blocks = []
                for n, m in enumerate(shareable[:STATUS_SOURCES], start=1):
                    row = self.store.raw(m["id"])
                    blocks.append(f"[{n}] {row['extracted_text'].strip()[:STATUS_CHARS]}")
                content = f"Notebook: {nb['name']}\n\nPassages:\n" + "\n\n".join(blocks)
                summary = providers.complete(config, f"{skill.instruction}\n\n{GROUNDING}", content, max_tokens=200).strip()
                used_model = True
            elif config is not None and members:
                summary = "Only private sources here, so nothing is shared for a summary."
            else:
                topics = _topics(members)
                count = len(members)
                summary = (
                    f"{count} source(s)" + (f", topics: {', '.join(topics)}." if topics else ".")
                    if members
                    else "No sources match yet."
                )
            notebooks_out.append(
                {
                    "id": nb["id"],
                    "name": nb["name"],
                    "member_count": len(members),
                    "sources": [{"name": m["name"], "private": m["private"]} for m in members],
                    "summary": summary,
                    "activity": self.activity.list(nb["id"], STATUS_ACTIVITY) if self.activity else [],
                }
            )
        brain = {"sources": len(all_sources), "private": sum(1 for s in all_sources if s["private"])}
        activity = self.activity.list(None, STATUS_ACTIVITY) if self.activity else []
        return {
            "answer": _render(brain, notebooks_out, activity),
            "citations": [],
            "mode": "model" if used_model else "extractive",
            "skill": skill.name,
            "status": {"brain": brain, "notebooks": notebooks_out, "activity": activity},
        }


def _extractive(passages: list[dict[str, Any]], citations: list[dict[str, Any]]) -> str:
    lines = ["From your Sources:"]
    for p, c in zip(passages, citations):
        body = " ".join(p["text"].split())
        lines.append(f"- {c['source_name']}: {body[:200]}{'…' if len(body) > 200 else ''} [{c['n']}]")
    return "\n".join(lines)


# ---- /status helpers
def _topics(members: list[dict[str, Any]], limit: int = 4) -> list[str]:
    counts: dict[str, int] = {}
    for m in members:
        for tag in m["tags"]:
            counts[tag] = counts.get(tag, 0) + 1
    return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]]


def _render(brain: dict[str, Any], notebooks: list[dict[str, Any]], activity: list[dict[str, Any]]) -> str:
    if brain["sources"] == 0 and not notebooks:
        return "Your Brain is empty. Add a Source to get started."
    private = f" ({brain['private']} private)" if brain["private"] else ""
    lines = [f"Your Brain: {brain['sources']} source(s){private}, {len(notebooks)} notebook(s)."]
    for nb in notebooks:
        lines.append("")
        lines.append(f"{nb['name']} ({nb['member_count']})")
        names = ", ".join(s["name"] + (" (private)" if s["private"] else "") for s in nb["sources"]) or "nothing yet"
        lines.append(f"  Sources: {names}")
        lines.append(f"  Summary: {nb['summary']}")
        if nb["activity"]:
            lines.append("  Recent: " + "; ".join(f"{a['kind']} {a['source_name']}" for a in nb["activity"]))
    if activity:
        lines.append("")
        lines.append("Recent activity: " + "; ".join(f"{a['kind']} {a['source_name']}" for a in activity))
    return "\n".join(lines)
