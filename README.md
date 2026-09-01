# Data Enrichment System

A company-to-decision-maker contact enrichment pipeline — rebuilt as a generalized,
open-source system.

Originally built as an internal work tool; this repo is a from-scratch rebuild using
generic, sanitized logic only. No employer-specific data, workflows, or branding.

## Status

🚧 Early development. DB models, config loading, and CLI skeleton are in place.
Domain discovery, contact enrichment, and CRM sync are not built yet — see
[open issues](https://github.com/codeapplied/data-enrichment-system/issues).

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
- `dataenrich discover` — run domain discovery (not yet implemented)

## License

MIT — see [LICENSE](LICENSE).
