from dataenrich.discovery.confidence import DomainVote, normalize_domain, resolve_confidence


def test_normalize_domain_strips_protocol_www_path():
    assert normalize_domain("https://www.Example.com/about/") == "example.com"
    assert normalize_domain("http://example.com") == "example.com"


def test_agreement_and_head_confirmed_is_high():
    votes = [DomainVote("example.com", "a"), DomainVote("example.com", "b")]
    assert resolve_confidence(votes, head_confirmed={"example.com": True}) == ("example.com", "high")


def test_agreement_without_confirmation_is_medium():
    votes = [DomainVote("example.com", "a"), DomainVote("example.com", "b")]
    assert resolve_confidence(votes, head_confirmed={"example.com": False}) == ("example.com", "medium")


def test_single_confirmed_vote_is_low():
    votes = [DomainVote("example.com", "a")]
    assert resolve_confidence(votes, head_confirmed={"example.com": True}) == ("example.com", "low")


def test_single_unconfirmed_vote_is_unresolved():
    votes = [DomainVote("example.com", "a")]
    assert resolve_confidence(votes, head_confirmed={"example.com": False}) == (None, "unresolved")


def test_no_votes_is_unresolved():
    assert resolve_confidence([]) == (None, "unresolved")
