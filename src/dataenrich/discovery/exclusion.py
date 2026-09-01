def is_excluded(domain: str, exclude_domains: list[str], exclude_domain_keywords: list[str]) -> bool:
    """A living blocklist, not a one-time setup — real-estate/procurement
    listing aggregators, directories, and generic tokens keep recurring as
    false-positive traps across unrelated searches, so this list is
    expected to grow from observed false positives, never treated as
    finished."""
    d = domain.lower()
    if d in {x.lower() for x in exclude_domains}:
        return True
    return any(kw.lower() in d for kw in exclude_domain_keywords)
