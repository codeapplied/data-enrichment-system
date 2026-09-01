"""Real Pipedrive CRM client — implements CRMClient against Pipedrive's
REST API v1, following the same shape already proven in the sibling
tender-tracking-system repo's integrations/pipedrive.py.

Honest limitation: Pipedrive has no built-in "website" field on
Organizations — it's a custom field, and the field's key is account-
specific. Organization dedup here falls back to name-based search (the
same approach the sibling repo uses) rather than the website-based dedup
the design notes call for as ideal. A real account's custom field key
could be wired in later; that's not generic enough to hardcode into a
public rebuild. Contact dedup by email has no such limitation — Pipedrive's
/persons/search supports it directly.

No live Pipedrive account was available to test this against in this
session — verified via mocked-HTTP-shape tests only (see
tests/test_pipedrive_client.py), the same honest-limitation pattern used
throughout the sibling repo's own integrations.
"""

import requests

from .base import CRMClient, CRMContact, CRMOrganization


class PipedriveError(Exception):
    pass


class PipedriveClient(CRMClient):
    name = "pipedrive"

    def __init__(self, api_token: str, domain: str, timeout: int = 30) -> None:
        self.api_token = api_token
        self.base_url = f"https://{domain}.pipedrive.com/api/v1"
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
        params = dict(params or {})
        params["api_token"] = self.api_token
        response = self.session.request(
            method, f"{self.base_url}{path}", params=params, json=json, timeout=self.timeout
        )
        if not response.ok:
            raise PipedriveError(f"{method} {path} failed: {response.status_code} {response.text}")
        data = response.json()
        if not data.get("success", True):
            raise PipedriveError(f"{method} {path} returned success=false: {data}")
        return data.get("data")

    def find_organization_by_website(self, website: str) -> CRMOrganization | None:
        # No native website field on Pipedrive orgs — name-based search as
        # a documented fallback (see module docstring).
        results = self._request("GET", "/organizations/search", params={"term": website, "fields": "name"})
        items = (results or {}).get("items", [])
        if not items:
            return None
        org = items[0]["item"]
        return CRMOrganization(id=str(org["id"]), name=org.get("name", ""), website=website)

    def create_organization(self, name: str, website: str) -> CRMOrganization:
        created = self._request("POST", "/organizations", json={"name": name})
        return CRMOrganization(id=str(created["id"]), name=name, website=website)

    def find_contact_by_email(self, email: str) -> CRMContact | None:
        results = self._request("GET", "/persons/search", params={"term": email, "fields": "email"})
        items = (results or {}).get("items", [])
        if not items:
            return None
        person = items[0]["item"]
        return CRMContact(id=str(person["id"]), email=email, name=person.get("name"), org_id=None)

    def create_contact(self, name: str | None, email: str, org_id: str) -> CRMContact:
        payload = {"name": name or email, "email": [email], "org_id": int(org_id)}
        created = self._request("POST", "/persons", json=payload)
        return CRMContact(id=str(created["id"]), email=email, name=name, org_id=org_id)

    def find_lead(self, org_id: str, title: str) -> str | None:
        results = self._request("GET", "/deals/search", params={"term": title, "fields": "title"})
        items = (results or {}).get("items", [])
        for item in items:
            deal = item["item"]
            deal_org = deal.get("org_id")
            deal_org_id = deal_org.get("value") if isinstance(deal_org, dict) else deal_org
            if str(deal_org_id) == str(org_id):
                return str(deal["id"])
        return None

    def create_lead(self, org_id: str, contact_id: str | None, title: str, note: str) -> str:
        payload: dict = {"title": title, "org_id": int(org_id)}
        if contact_id is not None:
            payload["person_id"] = int(contact_id)
        created = self._request("POST", "/deals", json=payload)
        deal_id = created["id"]
        self._request("POST", "/notes", json={"deal_id": deal_id, "content": note})
        return str(deal_id)
