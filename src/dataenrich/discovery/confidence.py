import re
from collections import Counter
from dataclasses import dataclass


def normalize_domain(url_or_domain: str) -> str:
    """Strip protocol/www/path/trailing-slash and lowercase — applied
    identically everywhere a domain is compared, to avoid the common bug
    class of near-duplicate keys (http vs https, www vs bare, trailing /)."""
    d = url_or_domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d


@dataclass
class DomainVote:
    domain: str
    source: str


def resolve_confidence(votes: list[DomainVote], head_confirmed: dict[str, bool] | None = None) -> tuple[str | None, str]:
    """Confidence is a hard architectural gate, not a soft score.

    - Two-or-more independent votes agree AND the domain is HEAD-confirmed
      to actually resolve -> "high" — only this tier proceeds automatically.
    - Votes agree but HEAD couldn't confirm (e.g. bot-protection blocked the
      request) -> "medium" — "agreement without confirmation": a blocked
      legitimate site would be worse to reject than to trust a bit more
      loosely, so this isn't a hard failure.
    - No agreement, but a single vote is at least HEAD-confirmed -> "low".
    - Nothing solid -> "unresolved" — parked for manual review, never
      silently dropped and never silently pushed downstream.
    """
    head_confirmed = head_confirmed or {}
    if not votes:
        return None, "unresolved"

    counts = Counter(v.domain for v in votes)
    top_domain, top_count = counts.most_common(1)[0]

    if top_count >= 2:
        return (top_domain, "high") if head_confirmed.get(top_domain, False) else (top_domain, "medium")

    if head_confirmed.get(top_domain, False):
        return top_domain, "low"

    return None, "unresolved"
