from dataenrich.config import EnrichmentRules
from dataenrich.pipeline.discover import run_discovery
from dataenrich.storage.models import Organization, SyncLog


def _seed(session, **overrides) -> Organization:
    org = Organization(
        raw_company_name=overrides.get("raw_company_name", "Sample Riverside Developments Inc."),
        project_name=overrides.get("project_name", "Riverside Commons Phase 2"),
        address=overrides.get("address", "100 Riverside Way, Sample City, ON"),
        status="pending",
    )
    session.add(org)
    session.commit()
    return org


def test_dry_run_makes_no_writes(db_session):
    org = _seed(db_session)
    result = run_discovery(db_session, apply=False, rules=EnrichmentRules())

    assert result.processed == 1
    assert result.resolved_high == 1
    db_session.refresh(org)
    assert org.status == "pending"
    assert org.domain is None
    assert db_session.query(SyncLog).count() == 0


def test_apply_resolves_high_confidence_and_logs(db_session):
    _seed(db_session)
    result = run_discovery(db_session, apply=True, rules=EnrichmentRules())

    assert result.resolved_high == 1
    org = db_session.query(Organization).one()
    assert org.status == "domain_resolved"
    assert org.domain == "sampleriversidedevelopments.example"
    assert org.domain_confidence == "high"

    log = db_session.query(SyncLog).one()
    assert log.stage == "domain_discovery"
    assert log.status == "success"
    assert log.records_new == 1
    assert log.records_flagged == 0


def test_all_excluded_is_parked_with_no_candidate_domain(db_session):
    _seed(
        db_session,
        raw_company_name="Sample Ghost Holdings LLC",
        project_name="Unnamed Parcel 9",
        address="Unknown, Sample City, MB",
    )
    result = run_discovery(
        db_session,
        apply=True,
        rules=EnrichmentRules(exclude_domain_keywords=["newsoutlet", "directory"]),
    )

    assert result.resolved_high == 0
    assert result.parked_for_review == 1
    org = db_session.query(Organization).one()
    assert org.status == "needs_review"
    assert org.domain_confidence == "unresolved"
    assert org.domain is None


def test_single_source_low_confidence_still_records_candidate_domain(db_session):
    """Excluding the aggregator false-positive leaves a single confirmed
    vote — parked (only "high" auto-proceeds), but the candidate domain is
    still recorded so a human reviewer has a starting point rather than a
    blank field."""
    _seed(
        db_session,
        raw_company_name="Sample Harbor Properties Ltd.",
        project_name="Harbor View Tower",
        address="12 Harbor St, Sample City, BC",
    )
    result = run_discovery(
        db_session,
        apply=True,
        rules=EnrichmentRules(exclude_domain_keywords=["aggregator"]),
    )

    assert result.resolved_high == 0
    assert result.parked_for_review == 1
    org = db_session.query(Organization).one()
    assert org.status == "needs_review"
    assert org.domain == "sampleharborproperties.example"
    assert org.domain_confidence == "low"


def test_field_level_authority_never_reprocesses_non_pending(db_session):
    _seed(db_session)
    run_discovery(db_session, apply=True, rules=EnrichmentRules())

    # simulate a human correcting the resolved org's domain by hand
    org = db_session.query(Organization).one()
    org.domain = "human-corrected.example"
    db_session.commit()

    result = run_discovery(db_session, apply=True, rules=EnrichmentRules())
    assert result.processed == 0

    db_session.refresh(org)
    assert org.domain == "human-corrected.example"
