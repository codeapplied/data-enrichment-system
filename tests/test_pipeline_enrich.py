from dataenrich.config import EnrichmentRules
from dataenrich.pipeline.enrich import run_enrichment
from dataenrich.storage.models import Contact, Organization, SyncLog

DEPT_PRIORITY = ["development", "construction", "property-management", "operations", "executive"]


def _seed(session, domain: str, status: str = "domain_resolved") -> Organization:
    org = Organization(
        raw_company_name="Sample Riverside Developments Inc.",
        domain=domain,
        domain_confidence="high",
        status=status,
    )
    session.add(org)
    session.commit()
    return org


def test_dry_run_makes_no_writes(db_session):
    org = _seed(db_session, "sampleriversidedevelopments.example")
    result = run_enrichment(db_session, apply=False, rules=EnrichmentRules(department_priority=DEPT_PRIORITY))

    assert result.processed == 1
    assert result.enriched == 1
    db_session.refresh(org)
    assert org.status == "domain_resolved"
    assert db_session.query(Contact).count() == 0
    assert db_session.query(SyncLog).count() == 0


def test_apply_ranks_by_department_priority_and_marks_enriched(db_session):
    org = _seed(db_session, "sampleriversidedevelopments.example")
    result = run_enrichment(db_session, apply=True, rules=EnrichmentRules(department_priority=DEPT_PRIORITY))

    assert result.enriched == 1
    db_session.refresh(org)
    assert org.status == "enriched"

    contacts = db_session.query(Contact).filter(Contact.organization_id == org.id).order_by(Contact.rank).all()
    assert len(contacts) == 3
    assert contacts[0].department == "development"  # not the vendor's default executive-first pick
    assert contacts[0].is_primary is True
    assert contacts[0].rank == 0

    log = db_session.query(SyncLog).one()
    assert log.stage == "contact_enrichment"
    assert log.records_new == 1
    assert log.records_flagged == 0


def test_thin_result_parks_for_review_instead_of_marking_enriched(db_session):
    org = _seed(db_session, "sampleharborproperties.example")
    result = run_enrichment(db_session, apply=True, rules=EnrichmentRules(department_priority=DEPT_PRIORITY))

    assert result.enriched == 0
    assert result.thin == 1
    db_session.refresh(org)
    assert org.status == "needs_review"
    assert db_session.query(Contact).count() == 0


def test_field_level_authority_never_reprocesses_non_domain_resolved(db_session):
    _seed(db_session, "sampleriversidedevelopments.example")
    run_enrichment(db_session, apply=True, rules=EnrichmentRules(department_priority=DEPT_PRIORITY))

    result = run_enrichment(db_session, apply=True, rules=EnrichmentRules(department_priority=DEPT_PRIORITY))
    assert result.processed == 0
