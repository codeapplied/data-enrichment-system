from dataenrich.discovery.query import build_queries


def test_normal_company_uses_name_first_queries():
    plan = build_queries("Sample Riverside Developments Inc.")
    assert plan.is_likely_shell_entity is False
    assert plan.queries[0] == '"Sample Riverside Developments Inc."'
    assert "official website" in plan.queries[1]


def test_numbered_entity_uses_project_and_address_first():
    plan = build_queries(
        "1234567 Ontario Inc.", project_name="Maple Grove Residences", address="45 Maple Grove Ave"
    )
    assert plan.is_likely_shell_entity is True
    assert "Maple Grove Residences" in plan.queries[0]
    assert "1234567 Ontario Inc." not in plan.queries[0]


def test_numbered_entity_falls_back_to_name_when_no_anchor():
    plan = build_queries("9876543 Canada Ltd.")
    assert plan.is_likely_shell_entity is True
    assert "9876543 Canada Ltd." in plan.queries[0]
