from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..config import EnrichmentRules, load_rules
from ..enrichment.base import ContactEnrichmentClient
from ..enrichment.ranking import rank_contacts
from ..enrichment.sandbox_client import SandboxEnrichmentClient
from ..storage.models import Contact, Organization, SyncLog, utcnow

TOP_N = 5


@dataclass
class EnrichmentRunResult:
    processed: int = 0
    enriched: int = 0
    thin: int = 0
    errors: list[str] = field(default_factory=list)
    previews: list[tuple[str, int, int]] = field(default_factory=list)


def _default_client() -> ContactEnrichmentClient:
    # Sandbox-only for now — swap in a real vendor once
    # enrichment/real_client_template.py has an actual implementation.
    return SandboxEnrichmentClient()


def run_enrichment(session: Session, apply: bool = False, rules: EnrichmentRules | None = None) -> EnrichmentRunResult:
    """Field-level authority again: only reads organizations already at
    status == "domain_resolved" (i.e. already past the domain-discovery
    confidence gate). A domain that resolves correctly but returns zero
    contacts ("thin") is parked back to "needs_review" rather than marked
    "enriched" with nothing in it — a correct-but-empty result and a wrong
    domain are different problems, and both deserve a human's attention,
    not a silent success.

    `rules` is injectable (defaults to load_rules()) so tests aren't tied
    to whatever local config file happens to exist on disk.
    """
    rules = rules if rules is not None else load_rules()
    client = _default_client()

    targets = session.query(Organization).filter(Organization.status == "domain_resolved").all()
    result = EnrichmentRunResult()

    for org in targets:
        result.processed += 1
        try:
            enrichment = client.enrich(org.domain)
        except Exception as exc:
            result.errors.append(f"{org.raw_company_name}: {exc}")
            continue

        raw_count = len(enrichment.raw_contacts)
        ranked = rank_contacts(enrichment.raw_contacts, rules.department_priority)
        selected = ranked[:TOP_N]
        result.previews.append((org.raw_company_name, raw_count, len(selected)))

        if raw_count == 0:
            result.thin += 1
        else:
            result.enriched += 1

        if apply:
            for idx, contact in enumerate(selected):
                session.add(
                    Contact(
                        organization_id=org.id,
                        name=contact.name,
                        title=contact.title,
                        department=contact.department,
                        seniority=contact.seniority,
                        email=contact.email,
                        verification_status=contact.verification_status,
                        rank=idx,
                        is_primary=(idx == 0),
                    )
                )
            org.status = "enriched" if raw_count > 0 else "needs_review"
            org.updated_at = utcnow()

    if apply:
        session.add(
            SyncLog(
                stage="contact_enrichment",
                started_at=utcnow(),
                finished_at=utcnow(),
                records_processed=result.processed,
                records_new=result.enriched,
                records_updated=0,
                records_flagged=result.thin,
                status="failed" if result.errors else "success",
                error_message="; ".join(result.errors) if result.errors else None,
            )
        )
        session.commit()

    return result
