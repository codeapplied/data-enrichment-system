import logging

import requests

logger = logging.getLogger(__name__)


def http_head_check(domain: str, timeout: int = 8) -> bool:
    """Confirms a domain actually resolves via a plain HTTP HEAD request.

    Necessary but not sufficient evidence of correctness on its own — this
    only answers "does something respond here"; the confidence gate in
    confidence.py is what decides whether that's enough (agreement plus
    confirmation is "high"; agreement without confirmation, e.g. because
    bot-protection blocked the HEAD request, is still "medium" rather than
    a hard failure — rejecting a real site would be worse than trusting an
    unconfirmed-but-agreed domain a bit more loosely).

    Any exception (timeout, connection refused, DNS failure, a WAF block)
    is treated as unconfirmed rather than raised, so one unreachable domain
    never aborts a discovery run.
    """
    for scheme in ("https://", "http://"):
        try:
            response = requests.head(f"{scheme}{domain}", timeout=timeout, allow_redirects=True)
            if response.status_code < 400:
                return True
        except requests.RequestException:
            logger.debug("HEAD check failed for %s%s", scheme, domain, exc_info=True)
            continue
    return False
