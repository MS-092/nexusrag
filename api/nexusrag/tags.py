from __future__ import annotations

import re
from collections import Counter

MAX_TAGS = 5
MIN_LENGTH = 4

STOPWORDS = frozenset(
    """
    about above after again against all also although always among and any are because been before being below
    between both but can could did does doing done down during each either else even ever every few for from further
    had has have having her here hers him his how however into its itself just like made make many may might more
    most much must neither nor not now off once only onto other our ours out over own per same shall she should since
    some such than that the their theirs them then there these they this those though through thus too under until
    upon very was were what when where whether which while who whom whose why will with within without would yet you
    your yours also appendix page pages table figure section report
    """.split()
)


def derive_tags(text: str, limit: int = MAX_TAGS) -> list[str]:
    """Top keywords by frequency, computed locally. Deterministic: ties break
    alphabetically. Numbers and common words are never tags."""
    words = re.findall(r"[a-z][a-z\-]{%d,}" % (MIN_LENGTH - 1), text.lower())
    counts = Counter(w.strip("-") for w in words if w.strip("-") not in STOPWORDS)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:limit]]
