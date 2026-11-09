"""Eval questions. expect = (source name, position check) or None for questions
the corpus cannot answer (the right behaviour is to refuse)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Q:
    question: str
    source: Optional[str]        # None = unanswerable
    page: Optional[int] = None
    sheet: Optional[str] = None
    row: Optional[int] = None    # a spreadsheet row the citation range must contain


QUESTIONS: list[Q] = [
    # --- PDF facts, page-level citations
    Q("What was revenue in Q3?", "finance.pdf", page=1),
    Q("How many people did headcount grow to?", "finance.pdf", page=2),
    Q("Which team was incident INC-7731 escalated to?", "ops-runbook.pdf", page=1),
    Q("What is the rollback procedure?", "ops-runbook.pdf", page=2),
    Q("How many days of annual leave do employees get?", "hr-policy.pdf", page=1),
    Q("How often can staff work remotely?", "hr-policy.pdf", page=2),
    Q("How long should I boil the spaghetti?", "cooking.pdf", page=1),
    Q("How long do I simmer the tomatoes?", "cooking.pdf", page=2),
    Q("How far away is the Orion Nebula?", "astronomy.pdf", page=1),
    Q("How many moons does Jupiter have?", "astronomy.pdf", page=2),
    # --- exact terms and codes
    Q("INC-7731", "ops-runbook.pdf", page=1),
    Q("SKU-5521", "inventory.xlsx", sheet="Warehouse", row=3),
    Q("SKU-7743", "inventory.xlsx", sheet="Returns", row=3),
    Q("Sparrowhawk", "Launch plan"),
    # --- tables: figures must come from the right row range
    Q("What is the revenue for Surabaya?", "sales.csv", sheet="CSV", row=78),
    Q("How many units did Surabaya sell?", "sales.csv", sheet="CSV", row=78),
    Q("How many SKU-4410 items are in the warehouse?", "inventory.xlsx", sheet="Warehouse", row=2),
    Q("Why was SKU-4410 returned?", "inventory.xlsx", sheet="Returns", row=2),
    Q("What is the quantity of the copper pipe?", "inventory.xlsx", sheet="Warehouse", row=3),
    # --- charts and images (read by local OCR)
    Q("How many units were sold in the Q3 chart?", "chart.png"),
    Q("What does the Q3 chart show?", "chart.png"),
    # --- notes
    Q("When does the beta ship?", "Launch plan"),
    Q("What theme does the launch use?", "Launch plan"),
    # --- unanswerable: the corpus has nothing relevant, so the right answer is a refusal
    Q("Who won the 1998 football world cup final?", None),
    Q("What is the capital of Mongolia?", None),
    Q("Explain how quantum entanglement works.", None),
    Q("What is the best way to learn the violin?", None),
    Q("Write a poem about the ocean.", None),
]
