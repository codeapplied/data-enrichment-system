import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class EnrichmentRules:
    department_priority: list[str] = field(default_factory=list)
    exclude_domains: list[str] = field(default_factory=list)
    exclude_domain_keywords: list[str] = field(default_factory=list)


@dataclass
class Settings:
    db_path: str
    search_api_key_primary: str | None
    search_api_key_secondary: str | None
    enrichment_api_key: str | None
    pipedrive_api_token: str | None
    pipedrive_domain: str | None


def load_settings() -> Settings:
    return Settings(
        db_path=os.getenv("DATAENRICH_DB_PATH", "data/enrichment.db"),
        search_api_key_primary=os.getenv("SEARCH_API_KEY_PRIMARY"),
        search_api_key_secondary=os.getenv("SEARCH_API_KEY_SECONDARY"),
        enrichment_api_key=os.getenv("ENRICHMENT_API_KEY"),
        pipedrive_api_token=os.getenv("PIPEDRIVE_API_TOKEN"),
        pipedrive_domain=os.getenv("PIPEDRIVE_DOMAIN"),
    )


def load_rules(config_path: str = "config/rules.yaml") -> EnrichmentRules:
    path = Path(config_path)
    if not path.exists():
        return EnrichmentRules()
    with path.open() as f:
        raw = yaml.safe_load(f) or {}
    return EnrichmentRules(
        department_priority=raw.get("department_priority", []),
        exclude_domains=raw.get("exclude_domains", []),
        exclude_domain_keywords=raw.get("exclude_domain_keywords", []),
    )


settings = load_settings()
