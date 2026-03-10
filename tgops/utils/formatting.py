"""Rich console helpers for TGOps CLI output."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from tgops.models.member import OffboardingJob
from tgops.models.migration import MigrationJob, MigrationStatus

console = Console()


def print_success(msg: str) -> None:
    """Print a success message in green."""
    console.print(f"[bold green]SUCCESS[/] {msg}")


def print_error(msg: str) -> None:
    """Print an error message in red."""
    console.print(f"[bold red]ERROR[/] {msg}")


def print_warning(msg: str) -> None:
    """Print a warning message in yellow."""
    console.print(f"[bold yellow]WARNING[/] {msg}")


def print_info(msg: str) -> None:
    """Print an info message in cyan."""
    console.print(f"[cyan]INFO[/] {msg}")


def make_table(title: str, columns: list[str], rows: list[list[str]]) -> Table:
    """Build and return a Rich Table."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    return table


def print_job_status(job: MigrationJob) -> None:
    """Print a formatted migration job status card."""
    status_color = {
        MigrationStatus.COMPLETE: "green",
        MigrationStatus.FAILED: "red",
        MigrationStatus.PENDING: "yellow",
    }.get(job.status, "cyan")

    console.rule(f"[bold]Migration Job[/] [dim]{job.job_id}[/]")
    console.print(f"  Source group : [bold]{job.source_group_id}[/]")
    console.print(f"  Target group : [bold]{job.target_group_id or 'not yet created'}[/]")
    console.print(f"  Status       : [{status_color}]{job.status.value}[/]")
    console.print(f"  Created at   : {job.created_at.isoformat()}")
    if job.completed_at:
        console.print(f"  Completed at : {job.completed_at.isoformat()}")
    if job.error:
        console.print(f"  Error        : [red]{job.error}[/]")

    if job.steps_completed:
        console.print("\n  Completed steps:")
        for step in job.steps_completed:
            console.print(f"    [green]✓[/] {step}")


def print_offboarding_status(job: OffboardingJob) -> None:
    """Print a formatted offboarding job status card."""
    status_color = "green" if job.status == "COMPLETE" else ("red" if job.status == "FAILED" else "yellow")

    console.rule(f"[bold]Offboarding Job[/] [dim]{job.job_id}[/]")
    console.print(f"  User         : {job.username or job.user_id}")
    console.print(f"  Mode         : [bold]{job.mode.value}[/]")
    console.print(f"  Status       : [{status_color}]{job.status}[/]")
    console.print(f"  Created at   : {job.created_at.isoformat()}")
    if job.completed_at:
        console.print(f"  Completed at : {job.completed_at.isoformat()}")

    if job.groups_found:
        console.print(f"\n  Groups found   : {len(job.groups_found)}")
    if job.groups_removed:
        console.print(f"  Groups removed : [green]{len(job.groups_removed)}[/]")
    if job.groups_skipped:
        console.print(f"  Groups skipped : [yellow]{len(job.groups_skipped)}[/]")
    if job.groups_failed:
        console.print(f"  Groups failed  : [red]{len(job.groups_failed)}[/]")
