import typer
from rich.console import Console
from rich.table import Table

from .config import load_rules, settings
from .storage.db import get_engine, get_session_factory, init_db
from .storage.models import SyncLog

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


@app.command()
def discover() -> None:
    """Run domain discovery for pending organizations."""
    console.print("[red]Pipeline not implemented yet — see upcoming phases.[/red]")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
