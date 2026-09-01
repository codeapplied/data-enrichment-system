from dataenrich.discovery.exclusion import is_excluded


def test_exact_domain_match_excluded():
    assert is_excluded("baddomain.com", ["baddomain.com"], []) is True


def test_keyword_match_excluded():
    assert is_excluded("some-aggregator-site.com", [], ["aggregator"]) is True


def test_unrelated_domain_not_excluded():
    assert is_excluded("realcompany.com", ["baddomain.com"], ["aggregator"]) is False
