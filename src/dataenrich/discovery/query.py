import re
from dataclasses import dataclass

# A purely mechanical pattern for Canadian-style numbered/shell entities
# (e.g. "1234567 Ontario Inc.") — their own name is nearly useless for
# search, so those get an address/project-first query instead of a
# name-first one. See design notes: generic search fails badly on these.
NUMBERED_ENTITY_PATTERN = re.compile(r"^\d{6,}\s")


@dataclass
class QueryPlan:
    """Two deliberately different query shapes, not a naive repeat-the-same-
    query retry. A first quoted exact-name search often surfaces news/
    directory aggregator pages that merely *mention* the company; dropping
    the quotes and adding an explicit qualifier is a different signal, not
    just another attempt at the same one."""

    queries: list[str]
    is_likely_shell_entity: bool


def build_queries(company_name: str, project_name: str | None = None, address: str | None = None) -> QueryPlan:
    company_name = company_name.strip()
    is_shell = bool(NUMBERED_ENTITY_PATTERN.match(company_name))

    if is_shell:
        anchor_parts = [p.strip() for p in (project_name, address) if p and p.strip()]
        anchor = " ".join(anchor_parts) if anchor_parts else company_name
        queries = [f'"{anchor}"', f"{anchor} official website"]
    else:
        queries = [f'"{company_name}"', f"{company_name} official website"]

    return QueryPlan(queries=queries, is_likely_shell_entity=is_shell)
