from .base import RawContact


def rank_contacts(contacts: list[RawContact], department_priority: list[str]) -> list[RawContact]:
    """Re-sorts by department relevance instead of the enrichment vendor's
    default seniority-first order — the vendor's default favors
    executive/C-suite contacts, but the real decision-maker function varies
    by buyer category (see design notes: roughly 40-50% of an early
    imported-contact batch had to be manually replaced by sales before this
    correction existed).

    A department not present in `department_priority` sorts last. Python's
    `sorted` is stable, so contacts tied on priority (including "not
    listed, sorts last") keep their original (vendor) relative order.
    """
    priority_index = {dept.lower(): i for i, dept in enumerate(department_priority)}
    unranked = len(department_priority)

    def key(contact: RawContact) -> int:
        dept = (contact.department or "").lower()
        return priority_index.get(dept, unranked)

    return sorted(contacts, key=key)
