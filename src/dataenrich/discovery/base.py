from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from .confidence import DomainVote, normalize_domain, resolve_confidence
from .exclusion import is_excluded
from .query import build_queries


@dataclass
class SearchResult:
    url: str


class SearchClient(ABC):
    """A pluggable search backend — one call per query string, returning
    ranked result URLs. Two *independent* SearchClient instances (different
    vendors, or a vendor plus a bundled fixture) are meant to be
    cross-checked against each other — that's what makes a "high
    confidence" match trustworthy rather than a first-guess."""

    name: str

    @abstractmethod
    def search(self, query: str) -> list[SearchResult]:
        raise NotImplementedError


@dataclass
class DiscoveryResult:
    domain: str | None
    confidence: str  # unresolved | low | medium | high
    method: str
    is_likely_shell_entity: bool
    excluded: bool = False


def discover_domain(
    company_name: str,
    clients: list[SearchClient],
    project_name: str | None = None,
    address: str | None = None,
    exclude_domains: list[str] | None = None,
    exclude_domain_keywords: list[str] | None = None,
    head_check: Callable[[str], bool] | None = None,
) -> DiscoveryResult:
    """Orchestrates one company through the full confidence-gated pipeline:
    build both query shapes, run every client, take each client's top
    non-excluded domain as its vote, then resolve confidence from how many
    independent votes agree plus (optionally) live domain confirmation.

    `head_check` is intentionally injected rather than hardcoded — the
    sandbox provider passes a fixture-backed stub, a real provider would
    pass an actual HTTP HEAD check. Keeps this function fully unit-testable
    with zero network access.
    """
    exclude_domains = exclude_domains or []
    exclude_domain_keywords = exclude_domain_keywords or []
    plan = build_queries(company_name, project_name=project_name, address=address)

    votes: list[DomainVote] = []
    any_result_seen = False
    any_vote_cast = False
    for client in clients:
        for query in plan.queries:
            results = client.search(query)
            for result in results:
                any_result_seen = True
                domain = normalize_domain(result.url)
                if is_excluded(domain, exclude_domains, exclude_domain_keywords):
                    continue
                votes.append(DomainVote(domain=domain, source=client.name))
                any_vote_cast = True
                break  # top non-excluded result only, per query
            if any_vote_cast:
                break  # one vote per client per query is enough signal
            any_vote_cast = False

    candidate_domains = {v.domain for v in votes}
    head_confirmed = {d: head_check(d) for d in candidate_domains} if head_check else {}

    domain, confidence = resolve_confidence(votes, head_confirmed=head_confirmed)
    # every result seen was filtered out by the exclusion list, not merely
    # "nothing found" — worth distinguishing for diagnosis (see design notes:
    # "raw found vs. selected" is a real diagnostic distinction).
    excluded = domain is None and any_result_seen and not votes

    return DiscoveryResult(
        domain=domain,
        confidence=confidence,
        method="dual-source-cross-check" if len(clients) >= 2 else "single-source",
        is_likely_shell_entity=plan.is_likely_shell_entity,
        excluded=excluded,
    )
