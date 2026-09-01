# Data Enrichment System

A company-to-decision-maker contact enrichment pipeline — rebuilt as a generalized,
open-source system.

Originally built as an internal work tool; this repo is a from-scratch rebuild using
generic, sanitized logic only. No employer-specific data, workflows, or branding.

## Status

🚧 Early development. Domain discovery and contact enrichment are both
built, wired into the CLI/DB pipeline, and unit-tested. CRM push is not
built yet — see
[open issues](https://github.com/codeapplied/data-enrichment-system/issues).

Try it end to end with zero setup beyond `uv venv && uv pip install -e .`:

```
dataenrich init
dataenrich seed-demo
dataenrich discover --apply  # resolves high-confidence orgs, parks the rest
dataenrich enrich --apply    # ranks+stores contacts for domain-resolved orgs
dataenrich status
```

## Domain discovery

`src/dataenrich/discovery/` — the confidence-gated engine that turns a raw
company/project/address record into a resolved domain, or parks it for
manual review:

- `query.py` — builds two deliberately different query shapes per company
  (not a naive repeat); numbered/shell-entity names (e.g. "1234567 Ontario
  Inc.") get a project-name/address-first query instead of a name-first one,
  since their own name is nearly useless for search.
- `confidence.py` — the actual gate: two independent search signals
  agreeing *and* a live domain confirmation is "high" (only this tier
  proceeds automatically); agreement without confirmation is "medium";
  a single confirmed signal is "low"; anything else is "unresolved" and
  parked for manual review, never silently dropped or silently pushed
  downstream.
- `exclusion.py` — a living blocklist (aggregators, directories, news
  sites, generic tokens) applied before a result ever becomes a vote.
- `base.py` — the `SearchClient` interface and `discover_domain()`
  orchestrator that ties the above together.
- `sandbox_client.py` — the default demo backend: bundled fixture data,
  zero network calls, zero API keys, proves the whole pipeline end-to-end.
- `real_search_client_template.py` + `http_head_check.py` — template for
  wiring in a real search vendor plus a working, real (not sandboxed) HTTP
  HEAD confirmation check.

Run `pytest` to see the confidence gate exercised against 5 scenarios
(clean agreement, a shell-entity name, an aggregator false-positive
correctly excluded, agreement-without-confirmation, and an all-excluded
case) — fully offline, no network or API keys required.

## Contact enrichment

`src/dataenrich/enrichment/` — turns a resolved domain into ranked,
stored contacts:

- `base.py` — the `ContactEnrichmentClient` interface and `RawContact`/
  `EnrichmentResult` types.
- `ranking.py` — re-sorts contacts by department relevance instead of
  the vendor's default seniority-first order. A department not in the
  configured priority list sorts last; ties keep the vendor's original
  order (stable sort).
- `sandbox_client.py` — the default demo backend: bundled fixture data,
  including one domain with zero contacts on purpose (a "thin" result —
  a correct domain the vendor just has nothing indexed for, a different
  failure mode from a wrong domain).
- `real_client_template.py` — template for wiring in a real vendor
  (e.g. a Hunter.io-style domain-based contact API).

## Architecture

Raw records (company name, project name, address) → domain discovery (confidence-gated,
cross-checked across independent signals) → only high-confidence domains proceed
automatically, everything else is parked for manual review → contact enrichment against
a domain-based third-party API → contacts re-ranked by department relevance instead of
the vendor's default seniority-first sort → push to CRM (organization → contact → lead,
each phase gated on the previous phase's log). Every stage is logged to `SyncLog`, which
the ops CLI reads for pipeline health.

## Setup

```
uv venv
uv pip install -e .
cp config/.env.example .env
cp config/rules.example.yaml config/rules.yaml
dataenrich init
```

## CLI

- `dataenrich init` — create the database
- `dataenrich status` — recent pipeline runs
- `dataenrich rules` — show the loaded department-priority and domain-exclusion rules
- `dataenrich seed-demo` — load the bundled sandbox fixture as pending organizations (demo/test data only — there's no CSV/Excel import for your own data yet)
- `dataenrich discover [--apply]` — run domain discovery for pending organizations. Plan-only by default. Only "high" confidence proceeds automatically (status → `domain_resolved`); everything else is parked (`needs_review`) — field-level authority means a later run never touches a non-`pending` organization again, so a human's manual correction always sticks
- `dataenrich enrich [--apply]` — run contact enrichment for domain-resolved organizations. Plan-only by default. Contacts are ranked by department priority and stored (top 5); a domain that resolves but returns zero contacts is parked back to `needs_review` rather than marked "enriched" with nothing in it — field-level authority applies here too (only `domain_resolved` rows are ever touched)

## License

MIT — see [LICENSE](LICENSE).
