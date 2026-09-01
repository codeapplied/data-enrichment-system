import json
from importlib import resources

from .base import SearchClient, SearchResult


def load_fixtures() -> list[dict]:
    data = resources.files("dataenrich.discovery.fixtures").joinpath("sample_organizations.json")
    return json.loads(data.read_text(encoding="utf-8"))


class SandboxSearchClient(SearchClient):
    """Default demo search backend: bundled synthetic data, not a real
    search API. Zero network calls, zero API keys needed — proves the
    confidence-gate pipeline end-to-end. Two independent instances
    (variant "a" and "b") simulate two independent real search vendors
    being cross-checked against each other; swap in
    `real_search_client_template.py` once you've picked and configured
    actual vendors.
    """

    def __init__(self, variant: str = "a") -> None:
        if variant not in ("a", "b"):
            raise ValueError("variant must be 'a' or 'b'")
        self.variant = variant
        self.name = f"sandbox-{variant}"
        self._records = load_fixtures()

    def search(self, query: str) -> list[SearchResult]:
        query_lower = query.lower()
        for record in self._records:
            fields = (record.get("company_name"), record.get("project_name"), record.get("address"))
            if any(field and field.lower() in query_lower for field in fields):
                urls = record[f"search_{self.variant}_results"]
                return [SearchResult(url=u) for u in urls]
        return []


def sandbox_head_check(domain: str) -> bool:
    """Bundled head_check stub, keyed by the fixture record whose
    resolved_domain matches — stands in for a real HTTP HEAD request
    (see http_head_check.py) so the sandbox path stays network-free."""
    for record in load_fixtures():
        if record.get("resolved_domain") == domain:
            return bool(record["head_resolves"])
    return False
