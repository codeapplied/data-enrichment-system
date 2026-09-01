import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from .config import load_rules, settings
from .storage.db import get_engine, get_session_factory, init_db
from .storage.models import Organization, SyncLog

app = typer.Typer(help="Data Enrichment System — ops CLI")
console = Console()


@app.command()
def init() -> None:
    """Initialize the database."""
    engine = get_engine(settings.db_path)
    init_db(engine)
    console.print(f"[green]Database initialized at {settings.db_path}[/green]")


@app.command()
def status() -> None:
    """Show pipeline health: recent stage runs."""
    engine = get_engine(settings.db_path)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        logs = session.query(SyncLog).order_by(SyncLog.started_at.desc()).limit(20).all()

    if not logs:
        console.print("[yellow]No pipeline runs recorded yet. Run 'dataenrich discover' first.[/yellow]")
        raise typer.Exit()

    table = Table(title="Recent Pipeline Runs")
    for column in ("Stage", "Started", "Status", "Processed", "New", "Updated", "Flagged"):
        table.add_column(column)
    for log in logs:
        table.add_row(
            log.stage,
            str(log.started_at),
            log.status,
            str(log.records_processed),
            str(log.records_new),
            str(log.records_updated),
            str(log.records_flagged),
        )
    console.print(table)


@app.command()
def rules() -> None:
    """Show the loaded department-priority and domain-exclusion rules."""
    r = load_rules()
    if not r.department_priority and not r.exclude_domains and not r.exclude_domain_keywords:
        console.print("[yellow]No rules configured. Copy config/rules.example.yaml to config/rules.yaml.[/yellow]")
        raise typer.Exit()
    console.print(f"Department priority ({len(r.department_priority)}): {', '.join(r.department_priority) or '-'}")
    console.print(f"Excluded domains: {len(r.exclude_domains)}")
    console.print(f"Excluded domain keywords: {len(r.exclude_domain_keywords)}")


@app.command(name="seed-demo")
def seed_demo() -> None:
    """Load the bundled sandbox fixture as pending organizations.
    Demo/test data only, not a real import feature — there's no CSV/Excel
    import path yet for your own prospect data."""
    from .discovery.sandbox_client import load_fixtures

    engine = get_engine(settings.db_path)
    session_factory = get_session_factory(engine)
    inserted = 0
    with session_factory() as session:
        existing_names = {name for (name,) in session.query(Organization.raw_company_name).all()}
        for record in load_fixtures():
            if record["company_name"] in existing_names:
                continue
            session.add(
                Organization(
                    raw_company_name=record["company_name"],
                    project_name=record.get("project_name"),
                    address=record.get("address"),
                    status="pending",
                )
            )
            inserted += 1
        session.commit()

    if inserted:
        console.print(f"[green]Seeded {inserted} demo organizations.[/green]")
    else:
        console.print("[yellow]Demo organizations already seeded.[/yellow]")


@app.command()
def discover(
    apply: bool = typer.Option(
        False, "--apply", help="Actually write changes. Default is plan-only (dry-run) — no DB writes."
    ),
) -> None:
    """Run domain discovery for pending organizations. Sandbox backend only
    for now (see discovery/real_search_client_template.py to wire in a real
    search vendor). Plan-only by default."""
    from .pipeline.discover import run_discovery

    engine = get_engine(settings.db_path)
    session_factory = get_session_factory(engine)
    with session_factory() as session:
        result = run_discovery(session, apply=apply)

    if result.processed == 0:
        console.print(
            "[yellow]No pending organizations. Run 'dataenrich seed-demo' first, or import your own data.[/yellow]"
        )
        raise typer.Exit()

    mode = (
        "[bold green]APPLIED[/bold green]"
        if apply
        else "[bold yellow]PLAN ONLY (dry-run) — pass --apply to write for real[/bold yellow]"
    )
    console.print(mode)

    table = Table(title="Domain Discovery Results")
    for column in ("Company", "Domain", "Confidence"):
        table.add_column(column)
    for company, domain, confidence in result.previews:
        table.add_row(escape(company), escape(domain or "-"), confidence)
    console.print(table)

    console.print(
        f"Processed: {result.processed}  High-confidence: {result.resolved_high}  "
        f"Parked for review: {result.parked_for_review}  Errors: {len(result.errors)}"
    )
    for msg in result.errors[:5]:
        console.print(f"[red]  {escape(msg)}[/red]")


if __name__ == "__main__":
    app()
