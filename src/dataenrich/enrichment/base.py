from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class RawContact:
    """A single contact as returned by an enrichment vendor, before
    department-priority re-ranking. `department`/`seniority` are the
    vendor's own classification — not assumed accurate, just what's
    available to rank against."""

    email: str
    name: str | None = None
    title: str | None = None
    department: str | None = None
    seniority: str | None = None
    verification_status: str | None = None


@dataclass
class EnrichmentResult:
    domain: str
    raw_contacts: list[RawContact] = field(default_factory=list)
    industry: str | None = None
    company_size_signal: str | None = None


class ContactEnrichmentClient(ABC):
    """A pluggable contact-enrichment backend — one domain in, a raw
    (unranked) contact list out. Ranking by department relevance happens
    separately (see ranking.py), deliberately kept out of the client so any
    vendor's raw ordering can be re-ranked the same way."""

    name: str

    @abstractmethod
    def enrich(self, domain: str) -> EnrichmentResult:
        raise NotImplementedError
