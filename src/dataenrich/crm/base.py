from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CRMOrganization:
    id: str
    name: str
    website: str | None


@dataclass
class CRMContact:
    id: str
    email: str
    name: str | None
    org_id: str | None


class CRMClient(ABC):
    """A pluggable CRM backend. Organization dedup keys on normalized
    website (not name — names vary too much in formatting to be a
    reliable key, per design notes); contact dedup keys on email; lead
    dedup keys on (org, title) — see pipeline/push_crm.py.
    """

    name: str

    @abstractmethod
    def find_organization_by_website(self, website: str) -> CRMOrganization | None:
        raise NotImplementedError

    @abstractmethod
    def create_organization(self, name: str, website: str) -> CRMOrganization:
        raise NotImplementedError

    @abstractmethod
    def find_contact_by_email(self, email: str) -> CRMContact | None:
        raise NotImplementedError

    @abstractmethod
    def create_contact(self, name: str | None, email: str, org_id: str) -> CRMContact:
        raise NotImplementedError

    @abstractmethod
    def find_lead(self, org_id: str, title: str) -> str | None:
        """Returns the CRM lead/deal id if one already exists for this
        (org, title) pair, else None."""
        raise NotImplementedError

    @abstractmethod
    def create_lead(self, org_id: str, contact_id: str | None, title: str, note: str) -> str:
        raise NotImplementedError
