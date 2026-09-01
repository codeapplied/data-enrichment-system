"""Template for a real search-API-backed SearchClient.

No real vendor is wired here — pick your own (Google Custom Search JSON
API, Brave Search API, SerpAPI, or similar), each with its own auth scheme
and response shape. The point of running TWO of these (different vendors)
side by side is what makes discover_domain()'s confidence gate meaningful —
a single vendor's first guess is exactly the failure mode the reference
system's own history warns against (see the private design notes: weak,
single-source domain matches were the single largest category of flagged
bad leads).

Copy this file, rename the class, and implement `search()` against your
chosen vendor's API. Keep API keys in `.env` (see config/.env.example),
never hardcoded. Pair it with `http_head_check.py` for the live domain
confirmation step, passed into `discover_domain()` as `head_check`.
"""

from .base import SearchClient, SearchResult


class RealSearchClientTemplate(SearchClient):
    name = "your-search-vendor-name"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def search(self, query: str) -> list[SearchResult]:
        raise NotImplementedError(
            "Implement authentication and result parsing against your chosen "
            "search vendor's API here. Return results ranked as the vendor "
            "ranks them — discover_domain() only looks at the top "
            "non-excluded result per query."
        )
