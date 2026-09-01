from dataenrich.enrichment.base import RawContact
from dataenrich.enrichment.ranking import rank_contacts


def _contact(department: str, email: str) -> RawContact:
    return RawContact(email=email, department=department)


def test_department_priority_overrides_vendor_default_order():
    contacts = [_contact("executive", "exec@x.example"), _contact("development", "dev@x.example")]
    ranked = rank_contacts(contacts, ["development", "construction", "executive"])
    assert [c.email for c in ranked] == ["dev@x.example", "exec@x.example"]


def test_unlisted_department_sorts_last():
    contacts = [_contact("marketing", "mkt@x.example"), _contact("development", "dev@x.example")]
    ranked = rank_contacts(contacts, ["development"])
    assert [c.email for c in ranked] == ["dev@x.example", "mkt@x.example"]


def test_stable_sort_preserves_original_order_on_ties():
    contacts = [_contact("executive", "a@x.example"), _contact("executive", "b@x.example")]
    ranked = rank_contacts(contacts, ["development", "executive"])
    assert [c.email for c in ranked] == ["a@x.example", "b@x.example"]


def test_empty_priority_list_keeps_original_order():
    contacts = [_contact("executive", "a@x.example"), _contact("development", "b@x.example")]
    ranked = rank_contacts(contacts, [])
    assert [c.email for c in ranked] == ["a@x.example", "b@x.example"]
