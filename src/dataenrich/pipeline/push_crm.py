from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from ..crm.base import CRMClient, CRMContact, CRMOrganization
from ..crm.sandbox_client import SandboxCRMClient
from ..storage.models import Contact, Lead, Organization, SyncLog, utcnow


@dataclass
class CRMPushRunResult:
    processed: int = 0
    pushed: int = 0
    errors: list[str] = field(default_factory=list)
    previews: list[tuple[str, str, str]] = field(default_factory=list)


def _default_client() -> CRMClient:
    # Sandbox-only for now — swap in crm/pipedrive_client.py once
    # PIPEDRIVE_API_TOKEN/PIPEDRIVE_DOMAIN are configured.
    return SandboxCRMClient()


def _build_note(org: Organization, contact: Contact | None) -> str:
    lines = [
        "Source: data-enrichment-system import",
        f"Raw company name: {org.raw_company_name}",
        f"Project: {org.project_name or '-'}",
        f"Address: {org.address or '-'}",
        f"Domain confidence: {org.domain_confidence} ({org.domain_discovery_method or '-'})",
    ]
    if contact is not None:
        lines.append(f"Primary contact: {contact.name or contact.email} ({contact.title or 'title unknown'})")
    return "\n".join(lines)


def run_crm_push(session: Session, apply: bool = False, client: CRMClient | None = None) -> CRMPushRunResult:
    """Field-level authority again: only reads organizations at
    status == "enriched" (already past both the domain-discovery and
    contact-enrichment gates). Three ordered find-or-create phases per
    organization — organization -> contact -> lead — so re-running is
    always safe, nothing gets duplicated. A lead is deliberately modeled
    per PROJECT (one per Organization row), not per company — see the
    `Lead` model's own docstring for why.

    True dry-run safety: in plan-only mode, no `create_*` method is ever
    called on the client — only the read-only `find_*` methods, so a
    dry-run genuinely cannot mutate the CRM (or, for the sandbox backend,
    the in-memory fake CRM) even if the same client instance is reused.
    """
    client = client if client is not None else _default_client()
    targets = session.query(Organization).filter(Organization.status == "enriched").all()
    result = CRMPushRunResult()

    for org in targets:
        result.processed += 1
        try:
            crm_org = client.find_organization_by_website(org.domain)
            org_is_new = crm_org is None
            if org_is_new:
                crm_org = (
                    client.create_organization(org.raw_company_name, org.domain)
                    if apply
                    else CRMOrganization(id="(new)", name=org.raw_company_name, website=org.domain)
                )

            primary = (
                session.query(Contact)
                .filter(Contact.organization_id == org.id, Contact.is_primary.is_(True))
                .first()
            )

            crm_contact = None
            if primary is not None:
                crm_contact = client.find_contact_by_email(primary.email)
                if crm_contact is None:
                    crm_contact = (
                        client.create_contact(primary.name, primary.email, crm_org.id)
                        if apply
                        else CRMContact(id="(new)", email=primary.email, name=primary.name, org_id=crm_org.id)
                    )

            title = org.project_name or org.raw_company_name
            crm_lead_id = client.find_lead(crm_org.id, title) if not org_is_new else None
            if crm_lead_id is None:
                crm_lead_id = (
                    client.create_lead(crm_org.id, crm_contact.id if crm_contact else None, title, _build_note(org, primary))
                    if apply
                    else "(new)"
                )
        except Exception as exc:
            result.errors.append(f"{org.raw_company_name}: {exc}")
            continue

        result.previews.append((org.raw_company_name, crm_org.id, crm_lead_id))
        result.pushed += 1

        if apply:
            org.crm_org_id = crm_org.id
            org.status = "pushed"
            org.updated_at = utcnow()
            if primary is not None and crm_contact is not None:
                primary.crm_contact_id = crm_contact.id
            session.add(
                Lead(
                    organization_id=org.id,
                    primary_contact_id=primary.id if primary is not None else None,
                    title=title,
                    crm_lead_id=crm_lead_id,
                )
            )

    if apply:
        session.add(
            SyncLog(
                stage="crm_push",
                started_at=utcnow(),
                finished_at=utcnow(),
                records_processed=result.processed,
                records_new=result.pushed,
                records_updated=0,
                records_flagged=len(result.errors),
                status="failed" if result.errors else "success",
                error_message="; ".join(result.errors) if result.errors else None,
            )
        )
        session.commit()

    return result
