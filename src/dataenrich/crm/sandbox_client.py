from .base import CRMClient, CRMContact, CRMOrganization


class SandboxCRMClient(CRMClient):
    """Default demo backend: an in-memory fake CRM, not a real Pipedrive
    account. Pre-seeded with one "existing" organization so dedup against
    pre-existing CRM data is actually exercised — not just dedup within a
    single run, which would miss the more important real-world case (a
    live pull of what's already in the CRM before deciding to create
    anything). Zero network calls, zero credentials.
    """

    name = "sandbox"

    def __init__(self) -> None:
        self._orgs: dict[str, CRMOrganization] = {}
        self._contacts: dict[str, CRMContact] = {}
        self._leads: dict[tuple[str, str], str] = {}
        self._next_id = 1

        seed_org = CRMOrganization(
            id="crm-org-seed-1",
            name="Sample Riverside Developments Inc.",
            website="sampleriversidedevelopments.example",
        )
        self._orgs[seed_org.website] = seed_org

    def _new_id(self, prefix: str) -> str:
        crm_id = f"{prefix}-{self._next_id}"
        self._next_id += 1
        return crm_id

    def find_organization_by_website(self, website: str) -> CRMOrganization | None:
        return self._orgs.get(website)

    def create_organization(self, name: str, website: str) -> CRMOrganization:
        org = CRMOrganization(id=self._new_id("crm-org"), name=name, website=website)
        self._orgs[website] = org
        return org

    def find_contact_by_email(self, email: str) -> CRMContact | None:
        return self._contacts.get(email)

    def create_contact(self, name: str | None, email: str, org_id: str) -> CRMContact:
        contact = CRMContact(id=self._new_id("crm-contact"), email=email, name=name, org_id=org_id)
        self._contacts[email] = contact
        return contact

    def find_lead(self, org_id: str, title: str) -> str | None:
        return self._leads.get((org_id, title))

    def create_lead(self, org_id: str, contact_id: str | None, title: str, note: str) -> str:
        lead_id = self._new_id("crm-lead")
        self._leads[(org_id, title)] = lead_id
        return lead_id
