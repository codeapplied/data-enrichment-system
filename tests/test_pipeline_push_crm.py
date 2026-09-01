from dataenrich.crm.sandbox_client import SandboxCRMClient
from dataenrich.pipeline.push_crm import run_crm_push
from dataenrich.storage.models import Contact, Lead, Organization, SyncLog


def _seed_org(session, *, domain, project_name, company_name="Sample Riverside Developments Inc."):
    org = Organization(
        raw_company_name=company_name,
        project_name=project_name,
        domain=domain,
        domain_confidence="high",
        status="enriched",
    )
    session.add(org)
    session.commit()

    contact = Contact(
        organization_id=org.id,
        name="Jamie Okoye",
        title="VP of Development",
        department="development",
        email=f"jamie.okoye+{org.id}@{domain}",
        rank=0,
        is_primary=True,
    )
    session.add(contact)
    session.commit()
    return org


def test_dry_run_makes_no_client_or_db_mutations(db_session):
    _seed_org(db_session, domain="freshdomain.example", project_name="Phase 1")
    client = SandboxCRMClient()
    orgs_before = dict(client._orgs)

    result = run_crm_push(db_session, apply=False, client=client)

    assert result.processed == 1
    assert result.pushed == 1
    assert client._orgs == orgs_before  # no create_* call ever reached the client
    assert db_session.query(Lead).count() == 0
    assert db_session.query(SyncLog).count() == 0


def test_apply_creates_org_contact_lead_and_marks_pushed(db_session):
    org = _seed_org(db_session, domain="freshdomain.example", project_name="Phase 1")
    client = SandboxCRMClient()

    result = run_crm_push(db_session, apply=True, client=client)

    assert result.pushed == 1
    db_session.refresh(org)
    assert org.status == "pushed"
    assert org.crm_org_id is not None

    lead = db_session.query(Lead).one()
    assert lead.organization_id == org.id
    assert lead.crm_lead_id is not None

    log = db_session.query(SyncLog).one()
    assert log.stage == "crm_push"
    assert log.records_new == 1


def test_org_dedup_against_preexisting_crm_record(db_session):
    """Two projects for the same already-known developer (the sandbox's
    pre-seeded domain) resolve to the SAME CRM organization, each getting
    its own lead — proves dedup against a live CRM pull, not just dedup
    within this run."""
    org1 = _seed_org(db_session, domain="sampleriversidedevelopments.example", project_name="Phase 1")
    org2 = _seed_org(db_session, domain="sampleriversidedevelopments.example", project_name="Phase 2")
    client = SandboxCRMClient()

    result = run_crm_push(db_session, apply=True, client=client)

    assert result.pushed == 2
    db_session.refresh(org1)
    db_session.refresh(org2)
    assert org1.crm_org_id == "crm-org-seed-1"
    assert org2.crm_org_id == "crm-org-seed-1"

    leads = db_session.query(Lead).all()
    assert len(leads) == 2
    assert {lead.title for lead in leads} == {"Phase 1", "Phase 2"}


def test_org_dedup_within_a_single_run_for_a_brand_new_domain(db_session):
    org1 = _seed_org(db_session, domain="newdeveloper.example", project_name="Phase 1")
    org2 = _seed_org(db_session, domain="newdeveloper.example", project_name="Phase 2")
    client = SandboxCRMClient()

    run_crm_push(db_session, apply=True, client=client)

    db_session.refresh(org1)
    db_session.refresh(org2)
    assert org1.crm_org_id == org2.crm_org_id
    assert len(client._orgs) == 2  # the pre-seeded one + this one newly-created org


def test_field_level_authority_never_reprocesses_non_enriched(db_session):
    _seed_org(db_session, domain="freshdomain.example", project_name="Phase 1")
    client = SandboxCRMClient()
    run_crm_push(db_session, apply=True, client=client)

    result = run_crm_push(db_session, apply=True, client=client)
    assert result.processed == 0
