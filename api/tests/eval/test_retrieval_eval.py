"""Retrieval eval. Proves the claim the project makes: answers about charts and
tables cite the right Source and position. Runs through the API with no provider
key, so it measures retrieval and citations, not a model.

Metrics (answerable questions):
  recall@4        the expected Source is among the cited Sources
  citation        a citation names the expected Source AND the right page / sheet rows
  top1            the first citation is the expected Source
Refusal (unanswerable questions): the API answers no_results instead of guessing.

Thresholds live in thresholds.json, set from the first green baseline.
"""
from __future__ import annotations

import json
from pathlib import Path

from tests.eval.corpus import upload_all
from tests.eval.questions import QUESTIONS, Q

THRESHOLDS = json.loads((Path(__file__).parent / "thresholds.json").read_text())


def position_ok(q: Q, citation: dict) -> bool:
    pos = citation["position"]
    if q.page is not None and pos.get("page") != q.page:
        return False
    if q.sheet is not None:
        if pos.get("sheet") != q.sheet or "rows" not in pos:
            return False
        if q.row is not None and not (pos["rows"][0] <= q.row <= pos["rows"][1]):
            return False
    return True


def run_eval(client, ids: dict[str, str]) -> dict:
    by_name = ids
    hits = cited = top1 = answerable = refused = unanswerable = 0
    misses: list[str] = []
    for q in QUESTIONS:
        body = client.post("/chat", json={"question": q.question}).json()
        if q.source is None:
            unanswerable += 1
            if body["mode"] == "no_results":
                refused += 1
            else:
                misses.append(f"should refuse: {q.question!r} -> {[c['source_name'] for c in body['citations']]}")
            continue
        answerable += 1
        want = by_name[q.source]
        cites = body["citations"]
        in_top = any(c["source_id"] == want for c in cites)
        hits += in_top
        top1 += bool(cites) and cites[0]["source_id"] == want
        ok = any(c["source_id"] == want and position_ok(q, c) for c in cites)
        cited += ok
        if not in_top or not ok:
            got = [(c["source_name"], c["position"]) for c in cites]
            misses.append(f"{q.question!r}: want {q.source} p={q.page} s={q.sheet} r={q.row}, got {got}")
    return {
        "answerable": answerable,
        "unanswerable": unanswerable,
        "recall_at_4": hits / answerable,
        "citation_correct": cited / answerable,
        "top1": top1 / answerable,
        "refusal": refused / unanswerable,
        "misses": misses,
    }


def test_retrieval_eval_meets_the_baseline_thresholds(client, app, capsys):
    ids = upload_all(client, app)
    for name, sid in ids.items():
        assert client.get(f"/sources/{sid}").json()["state"] == "ready", f"{name} did not ingest"

    report = run_eval(client, ids)
    with capsys.disabled():
        print("\n--- retrieval eval ---")
        for key in ("answerable", "unanswerable", "recall_at_4", "citation_correct", "top1", "refusal"):
            value = report[key]
            print(f"{key:18} {value:.3f}" if isinstance(value, float) else f"{key:18} {value}")
        for miss in report["misses"]:
            print("  miss:", miss)

    for metric, floor in THRESHOLDS.items():
        assert report[metric] >= floor, f"{metric} {report[metric]:.3f} fell below {floor}"


def test_the_corpus_and_questions_have_the_agreed_size():
    assert 20 <= len(QUESTIONS) <= 30
    assert sum(1 for q in QUESTIONS if q.source is None) >= 3
