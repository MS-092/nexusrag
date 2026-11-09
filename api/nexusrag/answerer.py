from __future__ import annotations

import math
import re
from typing import Any

from pathlib import Path

from nexusrag import captioner, providers
from nexusrag.embedder import Embedder
from nexusrag.index import Index
from nexusrag.providers import ProviderConfig
from nexusrag.sources import SourceStore

TOP_K = 4
# Calibrated on the local embedder with the eval corpus (tests/eval): the best hit for
# answerable questions scores >= 0.605 cosine, for unanswerable ones <= 0.559. The gate
# sits in the middle of that gap. Exact-term matches bypass it. The eval re-checks this.
MIN_SIMILARITY = 0.58
QUOTE_CHARS = 320
MAX_IMAGES = 2
NO_RESULTS = "There is not enough information in your Sources to answer that."

STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how", "does", "did", "is", "are", "was",
    "were", "the", "and", "for", "with", "from", "that", "this", "these", "those", "about", "into", "have",
    "has", "had", "tell", "give", "show", "please", "your", "you", "can", "could", "would", "should",
}

SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered passages provided. "
    "Cite the passages you rely on like [1] or [2]. "
    "If the passages do not contain the answer, say you do not have enough information. "
    "Never use outside knowledge and never invent numbers."
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9_.\-]{2,}", text.lower()) if t not in STOPWORDS}


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class Answerer:
    def __init__(self, store: SourceStore, index: Index, embedder: Embedder) -> None:
        self.store = store
        self.index = index
        self.embedder = embedder

    def retrieve(self, question: str, source_ids: set[str]) -> list[dict[str, Any]]:
        dense, sparse = self.embedder.embed_query(question)
        hits = self.index.search(dense, sparse, source_ids, k=TOP_K)
        q_tokens = _tokens(question)
        kept = []
        for hit in hits:
            similar = _cosine(dense, hit["vector"]) >= MIN_SIMILARITY
            exact = bool(q_tokens & _tokens(hit["text"]))   # rescues codes and names
            if similar or exact:
                kept.append(hit)
        return kept

    def _image_blocks(self, citations: list[dict[str, Any]]) -> list[dict]:
        """Original images for the top image hits, so the model can look at the real chart."""
        blocks: list[dict] = []
        seen: set[str] = set()
        for c in citations:
            if c["kind"] != "image" or c["source_id"] in seen or len(blocks) >= MAX_IMAGES:
                continue
            row = self.store.raw(c["source_id"])
            if row and row["file_path"]:
                seen.add(c["source_id"])
                blocks.append({"type": "text", "text": f"Image for passage [{c['n']}]:"})
                blocks.append(captioner.image_block(Path(row["file_path"])))
        return blocks

    def _citations(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for n, hit in enumerate(hits, start=1):
            source = self.store.get(hit["source_id"])
            out.append(
                {
                    "n": n,
                    "source_id": hit["source_id"],
                    "source_name": source["name"] if source else "Removed source",
                    "kind": source["kind"] if source else None,
                    "position": hit["position"],
                    "quote": hit["text"][:QUOTE_CHARS],
                    "removed": source is None,
                }
            )
        return out

    def answer(self, question: str, source_ids: set[str], config: ProviderConfig | None) -> dict[str, Any]:
        hits = self.retrieve(question, source_ids)
        if not hits:
            return {"answer": NO_RESULTS, "citations": [], "mode": "no_results"}
        citations = self._citations(hits)
        if config is None:
            return {"answer": _extractive(question, hits), "citations": citations, "mode": "extractive"}
        passages = "\n\n".join(
            f"[{c['n']}] {c['source_name']} {_where(c['position'])}\n{hit['text']}"
            for c, hit in zip(citations, hits)
        )
        content: providers.Content = f"Question: {question}\n\nPassages:\n{passages}"
        images = self._image_blocks(citations)
        if images:
            content = [{"type": "text", "text": content}, *images]
        text = providers.complete(config, SYSTEM_PROMPT, content)
        return {"answer": text, "citations": citations, "mode": "model"}


def _where(position: dict) -> str:
    if "sheet" in position:
        a, b = position["rows"]
        return f"(sheet {position['sheet']}, rows {a}-{b})"
    if "page" in position:
        return f"(page {position['page']})"
    return ""


def _extractive(question: str, hits: list[dict[str, Any]]) -> str:
    q = _tokens(question)
    lines = ["From your Sources:"]
    for n, hit in enumerate(hits[:2], start=1):
        candidates = [ln.strip() for ln in hit["text"].splitlines() if ln.strip()]
        best = max(candidates, key=lambda ln: len(q & _tokens(ln)), default=hit["text"])
        lines.append(f"- {best} [{n}]")
    return "\n".join(lines)
