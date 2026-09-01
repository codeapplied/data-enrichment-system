import json
from importlib import resources

from .base import ContactEnrichmentClient, EnrichmentResult, RawContact


def load_fixtures() -> dict:
    data = resources.files("dataenrich.enrichment.fixtures").joinpath("sandbox_contacts.json")
    return json.loads(data.read_text(encoding="utf-8"))


class SandboxEnrichmentClient(ContactEnrichmentClient):
    """Default demo backend: bundled fixture data, zero network calls, zero
    API keys. Deliberately includes one domain with an empty contact list
    (a resolved-but-thin result) — a real, documented failure mode (a
    correct domain that simply has no contacts the vendor has indexed),
    distinct from a wrong domain. Swap in `real_client_template.py` once
    you've picked and configured an actual vendor.
    """

    name = "sandbox"

    def __init__(self) -> None:
        self._records = load_fixtures()

    def enrich(self, domain: str) -> EnrichmentResult:
        record = self._records.get(domain)
        if record is None:
            return EnrichmentResult(domain=domain, raw_contacts=[])
        contacts = [RawContact(**c) for c in record["raw_contacts"]]
        return EnrichmentResult(
            domain=domain,
            raw_contacts=contacts,
            industry=record.get("industry"),
            company_size_signal=record.get("company_size_signal"),
        )
