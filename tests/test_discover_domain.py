from dataenrich.discovery.base import discover_domain
from dataenrich.discovery.sandbox_client import SandboxSearchClient, sandbox_head_check


def _clients():
    return [SandboxSearchClient("a"), SandboxSearchClient("b")]


def test_agreeing_sources_and_confirmed_head_is_high():
    result = discover_domain(
        "Sample Riverside Developments Inc.",
        clients=_clients(),
        project_name="Riverside Commons Phase 2",
        address="100 Riverside Way, Sample City, ON",
        head_check=sandbox_head_check,
    )
    assert result.domain == "sampleriversidedevelopments.example"
    assert result.confidence == "high"
    assert result.is_likely_shell_entity is False


def test_numbered_entity_resolves_via_project_and_address_anchor():
    result = discover_domain(
        "1234567 Ontario Inc.",
        clients=_clients(),
        project_name="Maple Grove Residences",
        address="45 Maple Grove Ave, Sample City, ON",
        head_check=sandbox_head_check,
    )
    assert result.domain == "maplegroveresidences.example"
    assert result.confidence == "high"
    assert result.is_likely_shell_entity is True


def test_aggregator_result_excluded_leaves_single_source_low_confidence():
    result = discover_domain(
        "Sample Harbor Properties Ltd.",
        clients=_clients(),
        project_name="Harbor View Tower",
        address="12 Harbor St, Sample City, BC",
        exclude_domain_keywords=["aggregator"],
        head_check=sandbox_head_check,
    )
    assert result.domain == "sampleharborproperties.example"
    assert result.confidence == "low"


def test_agreement_without_head_confirmation_is_medium():
    result = discover_domain(
        "Sample Quiet Construction Co.",
        clients=_clients(),
        project_name="Elm Street Infill",
        address="7 Elm St, Sample City, AB",
        head_check=sandbox_head_check,
    )
    assert result.domain == "samplequietconstruction.example"
    assert result.confidence == "medium"


def test_all_results_excluded_reports_excluded_not_silently_unresolved():
    result = discover_domain(
        "Sample Ghost Holdings LLC",
        clients=_clients(),
        project_name="Unnamed Parcel 9",
        address="Unknown, Sample City, MB",
        exclude_domain_keywords=["newsoutlet", "directory"],
        head_check=sandbox_head_check,
    )
    assert result.domain is None
    assert result.confidence == "unresolved"
    assert result.excluded is True
