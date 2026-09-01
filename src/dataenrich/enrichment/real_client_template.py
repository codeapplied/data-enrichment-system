"""Template for a real contact-enrichment vendor client.

No real vendor is wired here — pick your own (Hunter.io or similar
domain-based contact-lookup API). Copy this file, rename the class, and
implement `enrich()` against your chosen vendor's API. Keep API keys in
`.env` (see config/.env.example), never hardcoded.

Two things worth keeping from the reference system's own experience:
- Log the RAW contact count returned before any ranking/capping happens,
  separately from the count actually stored — a domain that's correct but
  has zero indexed contacts (small companies, no public staff directory)
  looks identical to "our filter was too aggressive" from the output
  alone unless you keep both numbers visible.
- Don't trust the vendor's default sort as "the right contact" — that's
  exactly what ranking.py's department-priority re-ranking exists to fix.
"""

from .base import ContactEnrichmentClient, EnrichmentResult


class RealEnrichmentClientTemplate(ContactEnrichmentClient):
    name = "your-enrichment-vendor-name"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def enrich(self, domain: str) -> EnrichmentResult:
        raise NotImplementedError(
            "Implement authentication and result parsing against your chosen "
            "enrichment vendor's API here."
        )
