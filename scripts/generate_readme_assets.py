"""Regenerate the CLI-output SVGs embedded in the README.

Runs the real CLI code paths (not a mockup) against a throwaway temp DB
populated by `seed-demo`, capturing Rich's actual rendered output (colors,
tables, box-drawing) to SVG. Re-run this after any change to the CLI's
table layouts so the README images stay accurate.

Usage: python scripts/generate_readme_assets.py
"""

import os
import shutil
import tempfile
from pathlib import Path

from rich.console import Console

REPO_ROOT = Path(__file__).parent.parent
ASSETS_DIR = REPO_ROOT / "docs" / "assets"


def main() -> None:
    tmp_dir = Path(tempfile.mkdtemp(prefix="dataenrich-assets-"))
    original_cwd = Path.cwd()

    try:
        (tmp_dir / "config").mkdir()
        shutil.copy(REPO_ROOT / "config" / "rules.example.yaml", tmp_dir / "config" / "rules.yaml")

        os.chdir(tmp_dir)

        import dataenrich.cli as cli_module
        from dataenrich.config import settings as demo_settings

        demo_settings.db_path = str(tmp_dir / "demo.db")
        demo_settings.pipedrive_api_token = None
        demo_settings.pipedrive_domain = None

        ASSETS_DIR.mkdir(parents=True, exist_ok=True)

        cli_module.init()
        cli_module.seed_demo()

        # --- dataenrich discover --apply ---------------------------------
        console = Console(record=True, width=100)
        cli_module.console = console
        cli_module.discover(apply=True)
        console.save_svg(str(ASSETS_DIR / "cli-discover.svg"), title="dataenrich discover --apply")

        # --- dataenrich enrich --apply ------------------------------------
        console = Console(record=True, width=100)
        cli_module.console = console
        cli_module.enrich(apply=True)
        console.save_svg(str(ASSETS_DIR / "cli-enrich.svg"), title="dataenrich enrich --apply")

        # --- dataenrich push-crm (plan-only, shows dedup against the ------
        # --- sandbox's pre-seeded org) -------------------------------------
        console = Console(record=True, width=100)
        cli_module.console = console
        cli_module.push_crm(apply=False)
        console.save_svg(str(ASSETS_DIR / "cli-push-crm.svg"), title="dataenrich push-crm")

        # --- dataenrich status ---------------------------------------------
        console = Console(record=True, width=100)
        cli_module.console = console
        cli_module.status()
        console.save_svg(str(ASSETS_DIR / "cli-status.svg"), title="dataenrich status")

        print(f"Wrote SVGs to {ASSETS_DIR}")

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
