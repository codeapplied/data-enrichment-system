from dataclasses import dataclass


@dataclass
class WriteDecision:
    action: str  # "write" | "skip_conflict"
    reason: str


def decide_write(current_value: str | None, new_value: str) -> WriteDecision:
    """The shared overwrite-protection gate every CRM-write path funnels
    through, rather than each call site trusting its own judgment: diffs
    the live CRM value against the value about to be written and only
    auto-approves the SAFE cases (empty in CRM, or identical). A real
    conflict — CRM already has a different non-empty value — is never
    silently overwritten; it's reported for a human to resolve, the same
    "surface drift, never auto-resolve it" principle used throughout this
    rebuild (see the domain-discovery confidence gate and the
    reconciliation approach in the sibling tender-tracking-system repo).
    """
    if not current_value:
        return WriteDecision("write", "empty in CRM")
    if current_value == new_value:
        return WriteDecision("write", "identical value")
    return WriteDecision("skip_conflict", f"CRM has {current_value!r}, would write {new_value!r}")
