from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import EnrichmentRules, load_rules
from ..discovery.base import SearchClient, discover_domain
from ..discovery.sandbox_client import SandboxSearchClient, sandbox_head_check
from ..storage.models import Organization, SyncLog, utcnow


@dataclass
class DiscoveryRunResult:
    processed: int = 0
    resolved_high: int = 0
    parked_for_review: int = 0
    errors: list[str] = field(default_factory=list)
    previews: list[tuple[str, str | None, str]] = field(default_factory=list)


def _default_clients() -> list[SearchClient]:
    # Sandbox-only for now — swap in a real vendor once
    # discovery/real_search_client_template.py has an actual implementation
    # behind it. Kept as its own function so the pipeline doesn't hardcode
    # the choice inline.
    return [SandboxSearchClient("a"), SandboxSearchClient("b")]


def run_discovery(session: Session, apply: bool = False, rules: EnrichmentRules | None = None) -> DiscoveryRunResult:
    """Field-level authority, not blanket automation: only ever reads
    organizations still in "pending" status. Anything already parked
    ("needs_review") or already resolved is never silently re-processed on
    a later run — a human (or a later phase) has to move it forward
    explicitly, the same principle the reference system's own CRM-write
    gate was built around.

    Only "high" confidence proceeds automatically (status -> "domain_resolved").
    "medium"/"low"/"unresolved" are all parked ("needs_review") — the
    candidate domain is still recorded for medium/low so a human reviewer
    has a starting point, but nothing auto-promotes past the gate.

    `rules` is injectable (defaults to the real config/rules.yaml via
    load_rules()) so tests can pass a controlled EnrichmentRules() instead
    of depending on whatever local config file happens to exist on disk.
    """
    rules = rules if rules is not None else load_rules()
    pending = session.query(Organization).filter(Organization.status == "pending").all()

    result = DiscoveryRunResult()
    for org in pending:
        result.processed += 1
        try:
            discovery = discover_domain(
                org.raw_company_name,
                clients=_default_clients(),
                project_name=org.project_name,
                address=org.address,
                exclude_domains=rules.exclude_domains,
                exclude_domain_keywords=rules.exclude_domain_keywords,
                head_check=sandbox_head_check,
            )
        except Exception as exc:
            result.errors.append(f"{org.raw_company_name}: {exc}")
            continue

        result.previews.append((org.raw_company_name, discovery.domain, discovery.confidence))

        if discovery.confidence == "high":
            result.resolved_high += 1
            new_status = "domain_resolved"
        else:
            result.parked_for_review += 1
            new_status = "needs_review"

        if apply:
            org.domain = discovery.domain
            org.domain_confidence = discovery.confidence
            org.domain_discovery_method = discovery.method
            org.status = new_status
            org.updated_at = utcnow()

    if apply:
        session.add(
            SyncLog(
                stage="domain_discovery",
                started_at=utcnow(),
                finished_at=utcnow(),
                records_processed=result.processed,
                records_new=result.resolved_high,
                records_updated=0,
                records_flagged=result.parked_for_review,
                status="failed" if result.errors else "success",
                error_message="; ".join(result.errors) if result.errors else None,
            )
        )
        session.commit()

    return result
