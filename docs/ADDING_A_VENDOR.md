# Adding a real vendor

Every external integration point in this project ships with a working,
network-free sandbox backend as the default. Swapping in a real vendor
means implementing the same interface and pointing `pipeline/*.py`'s
`_default_client()` at it instead — orchestration, the confidence gate,
ranking, and dedup logic don't change.

## 1. Search vendor (domain discovery)

Copy `discovery/real_search_client_template.py`, implement `search()`
against your chosen search API (Google Custom Search JSON API, Brave
Search API, SerpAPI, or similar):

```python
# src/dataenrich/discovery/my_search_vendor.py
from .base import SearchClient, SearchResult

class MySearchVendorClient(SearchClient):
    name = "my-search-vendor"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str) -> list[SearchResult]:
        # call the vendor's API, return ranked result URLs
        ...
```

Run **two independent instances** (different vendors, or one real vendor
plus the sandbox as a sanity check) — `discover_domain()`'s confidence
gate is only meaningful when it's cross-checking genuinely independent
signals, not the same vendor called twice. Pair it with
`http_head_check.py` (already real, no vendor needed) as the `head_check`
argument.

Wire it into `pipeline/discover.py`'s `_default_clients()`:

```python
def _default_clients() -> list[SearchClient]:
    return [MySearchVendorClient(settings.search_api_key_primary), AnotherVendorClient(...)]
```

## 2. Contact-enrichment vendor

Copy `enrichment/real_client_template.py`, implement `enrich()`:

```python
# src/dataenrich/enrichment/my_enrichment_vendor.py
from .base import ContactEnrichmentClient, EnrichmentResult, RawContact

class MyEnrichmentVendorClient(ContactEnrichmentClient):
    name = "my-enrichment-vendor"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def enrich(self, domain: str) -> EnrichmentResult:
        # call the vendor's domain-based contact lookup API
        ...
```

Two things worth keeping from the reference system's own experience (see
the module's own docstring): log the *raw* contact count separately from
the count actually stored, and don't trust the vendor's default sort —
`enrichment/ranking.py`'s department-priority re-ranking runs on whatever
`enrich()` returns regardless of vendor.

Wire it into `pipeline/enrich.py`'s `_default_client()`.

## 3. CRM

`crm/pipedrive_client.py` is already a real, working Pipedrive client —
not a template. If Pipedrive is your CRM, set `PIPEDRIVE_API_TOKEN` and
`PIPEDRIVE_DOMAIN` in `.env` and swap `pipeline/push_crm.py`'s
`_default_client()`:

```python
def _default_client() -> CRMClient:
    from ..crm.pipedrive_client import PipedriveClient
    return PipedriveClient(settings.pipedrive_api_token, settings.pipedrive_domain)
```

For a different CRM, implement the `CRMClient` interface (`crm/base.py`):
`find_organization_by_website`/`create_organization`,
`find_contact_by_email`/`create_contact`, `find_lead`/`create_lead`. Keep
organization dedup on a normalized website field if your CRM has one —
`pipedrive_client.py`'s own docstring documents why it had to fall back to
name-based search instead (Pipedrive has no native website field), which
is a real, non-generic limitation worth avoiding if your CRM does better.

Route every write through `crm/overwrite_gate.py`'s `decide_write()`
before updating a field on an already-found record — this project's
"surface a conflict, never silently overwrite" principle applies to a real
CRM exactly the way it does to the sandbox one.

## 4. Test it

```
dataenrich seed-demo         # or your own data, once a real import path exists
dataenrich discover          # plan-only — see what it would resolve, no writes
dataenrich discover --apply
dataenrich enrich --apply
dataenrich push-crm          # plan-only — no CRM writes at all, not even to sandbox
dataenrich push-crm --apply
dataenrich status
```

Write unit tests for a real vendor's request/response shape following
`tests/test_pipedrive_client.py`'s mocked-HTTP pattern (`unittest.mock.patch`
on `requests.Session.request`) — no live credentials needed to verify the
shape of what your client sends and how it parses what comes back.
