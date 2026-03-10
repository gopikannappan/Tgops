"""TGOps CLI entrypoint — Typer + Rich."""

from __future__ import annotations

import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from tgops.core.config import Settings, load_config

console = Console()
app = typer.Typer(
    name="tgops",
    help="Self-hostable Telegram community ops toolkit.",
    add_completion=False,
    no_args_is_help=True,
)

# Sub-command groups
account_app = typer.Typer(help="Manage the Telegram org account.", no_args_is_help=True)
group_app = typer.Typer(help="Inspect and snapshot groups.", no_args_is_help=True)
migrate_app = typer.Typer(help="Run and manage group migrations.", no_args_is_help=True)
admin_app = typer.Typer(help="Manage group admin rosters.", no_args_is_help=True)
invite_app = typer.Typer(help="Manage group invite links.", no_args_is_help=True)
member_app = typer.Typer(help="Member lookup and offboarding.", no_args_is_help=True)

app.add_typer(account_app, name="account")
app.add_typer(group_app, name="group")
app.add_typer(migrate_app, name="migrate")
app.add_typer(admin_app, name="admin")
app.add_typer(invite_app, name="invite")
app.add_typer(member_app, name="member")


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

@dataclass
class State:
    settings: Settings | None = None
    dry_run: bool = False
    verbose: bool = False


_state = State()


def get_settings() -> Settings:
    if _state.settings is None:
        _state.settings = load_config()
    return _state.settings


def run(coro):
    """Run an async coroutine from a sync Typer callback."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Global options callback
# ---------------------------------------------------------------------------

@app.callback()
def main_callback(
    ctx: typer.Context,
    config: Optional[str] = typer.Option(None, "--config", help="Path to tgops.yaml config file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip destructive API calls."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging."),
):
    """TGOps — Telegram community ops toolkit."""
    import logging

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    try:
        settings = load_config(config)
    except Exception as exc:
        # Defer config errors — some subcommands may not need config (e.g. --help)
        _state.settings = None
        return

    if dry_run:
        # Override dry_run from CLI flag
        object.__setattr__(settings, "dry_run", True) if hasattr(settings, "__dataclass_fields__") else None
        # Pydantic model — rebuild with overridden value
        settings = settings.model_copy(update={"dry_run": True})

    _state.settings = settings
    _state.dry_run = dry_run
    _state.verbose = verbose


def _make_client():
    """Create a TGOpsClient from current settings."""
    from tgops.core.client import TGOpsClient
    return TGOpsClient(get_settings())


# ---------------------------------------------------------------------------
# account commands
# ---------------------------------------------------------------------------

@account_app.command("setup")
def account_setup():
    """Interactive OTP wizard — authenticate the org account."""
    async def _run():
        from tgops.services.account import AccountService
        client = _make_client()
        svc = AccountService(client, get_settings())
        await svc.setup()
        await client.stop()
    run(_run())


@account_app.command("status")
def account_status():
    """Show current account status and session info."""
    from tgops.utils.formatting import make_table, print_error, print_info, print_success

    async def _run():
        from tgops.services.account import AccountService
        client = _make_client()
        svc = AccountService(client, get_settings())
        info = await svc.status()
        await client.stop()

        rows = [
            ["Phone", info["phone"]],
            ["Session path", info["session_path"]],
            ["Authorized", str(info["is_authorized"])],
            ["Group count", str(info["group_count"])],
        ]
        if info.get("me"):
            me = info["me"]
            rows.insert(0, ["User ID", str(me.get("id", ""))])
            rows.insert(1, ["Name", f"{me.get('first_name', '')} {me.get('last_name', '') or ''}".strip()])
            rows.insert(2, ["Username", me.get("username") or "(none)"])

        table = make_table("Account Status", ["Field", "Value"], rows)
        console.print(table)

    run(_run())


@account_app.command("verify")
def account_verify():
    """Verify that the session is valid and authorized."""
    from tgops.utils.formatting import print_error, print_success

    async def _run():
        from tgops.services.account import AccountService
        client = _make_client()
        svc = AccountService(client, get_settings())
        ok = await svc.verify()
        await client.stop()
        if ok:
            print_success("Session is valid.")
        else:
            print_error("Session is NOT valid. Run 'tgops account setup'.")
            raise typer.Exit(1)

    run(_run())


# ---------------------------------------------------------------------------
# group commands
# ---------------------------------------------------------------------------

@group_app.command("list")
def group_list():
    """List all groups the org account is a member of."""
    from tgops.utils.formatting import make_table

    async def _run():
        client = _make_client()
        await client.start()
        rows = []
        async for dialog in client.client.get_dialogs():
            if dialog.chat and dialog.chat.type.name in ("GROUP", "SUPERGROUP"):
                chat = dialog.chat
                rows.append([
                    str(chat.id),
                    getattr(chat, "title", ""),
                    getattr(chat, "username", "") or "",
                    str(getattr(chat, "members_count", "") or ""),
                ])
        await client.stop()
        table = make_table(
            "Groups", ["ID", "Title", "Username", "Members"], rows
        )
        console.print(table)

    run(_run())


@group_app.command("inspect")
def group_inspect(
    group_id: int = typer.Argument(..., help="Telegram group ID"),
):
    """Show detailed info about a specific group."""
    from tgops.utils.formatting import make_table

    async def _run():
        client = _make_client()
        await client.start()
        chat = await client.call("get_chat", group_id)
        await client.stop()

        rows = [
            ["ID", str(chat.id)],
            ["Title", getattr(chat, "title", "")],
            ["Username", getattr(chat, "username", "") or ""],
            ["Type", str(getattr(chat, "type", ""))],
            ["Members", str(getattr(chat, "members_count", "") or "")],
            ["Description", (getattr(chat, "description", "") or "")[:80]],
            ["Invite link", getattr(chat, "invite_link", "") or ""],
        ]
        table = make_table(f"Group {group_id}", ["Field", "Value"], rows)
        console.print(table)

    run(_run())


@group_app.command("snapshot")
def group_snapshot(
    group_id: int = typer.Argument(..., help="Telegram group ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output JSON path"),
):
    """Capture a GroupState snapshot to JSON (and audit log)."""
    from tgops.utils.formatting import print_success

    async def _run():
        from tgops.core.audit import AuditEntry, AuditLogger
        from tgops.models.group import GroupState

        client = _make_client()
        settings = get_settings()
        await client.start()
        chat = await client.call("get_chat", group_id)
        await client.stop()

        snapshot = GroupState(
            group_id=chat.id,
            title=getattr(chat, "title", str(group_id)),
            username=getattr(chat, "username", None),
            owner_user_id=0,
            member_count=getattr(chat, "members_count", 0) or 0,
            invite_link=getattr(chat, "invite_link", None),
        )

        data = {
            "group_id": snapshot.group_id,
            "title": snapshot.title,
            "username": snapshot.username,
            "owner_user_id": snapshot.owner_user_id,
            "member_count": snapshot.member_count,
            "invite_link": snapshot.invite_link,
            "snapshot_at": snapshot.snapshot_at.isoformat(),
        }

        if output:
            Path(output).write_text(json.dumps(data, indent=2))
            print_success(f"Snapshot saved to {output}")
        else:
            console.print_json(json.dumps(data, indent=2))

        audit = AuditLogger(settings.audit_log_path)
        await audit.log(
            AuditEntry(event="group.snapshot", group_id=group_id, details=data)
        )

    run(_run())


# ---------------------------------------------------------------------------
# migrate commands
# ---------------------------------------------------------------------------

@migrate_app.command("plan")
def migrate_plan(
    group_id: int = typer.Argument(..., help="Source group ID to migrate"),
):
    """Show the migration step plan (dry run, no API calls)."""
    async def _run():
        from tgops.services.migration import MigrationService
        client = _make_client()
        svc = MigrationService(client, get_settings())
        plan = await svc.plan(group_id)
        console.print_json(json.dumps(plan, indent=2))

    run(_run())


@migrate_app.command("run")
def migrate_run(
    group_id: int = typer.Argument(..., help="Source group ID to migrate"),
    new_title: Optional[str] = typer.Option(None, "--new-title", help="Title for the new group"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip confirmation prompt"),
):
    """Execute a full 10-step group migration."""
    from tgops.utils.formatting import print_info, print_success, print_warning

    if not no_confirm:
        print_warning(f"About to migrate group {group_id}. This is irreversible.")
        confirmed = typer.confirm("Proceed?")
        if not confirmed:
            print_info("Aborted.")
            raise typer.Exit(0)

    async def _run():
        from tgops.services.migration import MigrationService
        client = _make_client()
        await client.start()
        svc = MigrationService(client, get_settings())
        job = await svc.run(group_id, new_title=new_title)
        await client.stop()

        from tgops.utils.formatting import print_job_status
        print_job_status(job)

    run(_run())


@migrate_app.command("status")
def migrate_status(
    job_id: str = typer.Argument(..., help="Migration job ID"),
):
    """Show the status of a migration job."""
    async def _run():
        from tgops.services.migration import MigrationService
        from tgops.utils.formatting import print_job_status

        client = _make_client()
        svc = MigrationService(client, get_settings())
        job = await svc.status(job_id)
        print_job_status(job)

    run(_run())


@migrate_app.command("resume")
def migrate_resume(
    job_id: str = typer.Argument(..., help="Migration job ID to resume"),
):
    """Resume a failed or interrupted migration job."""
    async def _run():
        from tgops.services.migration import MigrationService
        from tgops.utils.formatting import print_job_status

        client = _make_client()
        await client.start()
        svc = MigrationService(client, get_settings())
        job = await svc.resume(job_id)
        await client.stop()
        print_job_status(job)

    run(_run())


@migrate_app.command("batch")
def migrate_batch(
    file: str = typer.Option(..., "--file", "-f", help="File with one group ID per line"),
    concurrency: int = typer.Option(1, "--concurrency", help="Concurrency level (default: 1, sequential)"),
):
    """Run sequential migrations for multiple groups listed in a file."""
    from tgops.utils.formatting import print_info, print_job_status

    group_ids = []
    for line in Path(file).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            group_ids.append(int(line))

    print_info(f"Starting batch migration of {len(group_ids)} groups...")

    async def _run():
        from tgops.services.migration import MigrationService
        client = _make_client()
        await client.start()
        svc = MigrationService(client, get_settings())
        jobs = await svc.batch(group_ids)
        await client.stop()
        for job in jobs:
            print_job_status(job)

    run(_run())


# ---------------------------------------------------------------------------
# admin commands
# ---------------------------------------------------------------------------

@admin_app.command("list")
def admin_list(
    group_id: int = typer.Argument(..., help="Group ID"),
):
    """List all admins in a group."""
    from tgops.utils.formatting import make_table

    async def _run():
        from tgops.services.admin import AdminService
        client = _make_client()
        await client.start()
        svc = AdminService(client, get_settings())
        admins = await svc.list(group_id)
        await client.stop()

        rows = [
            [str(a.user_id), a.username or "", a.added_at.isoformat() if a.added_at else ""]
            for a in admins
        ]
        table = make_table(f"Admins in group {group_id}", ["User ID", "Username", "Added At"], rows)
        console.print(table)

    run(_run())


@admin_app.command("add")
def admin_add(
    group_id: int = typer.Argument(..., help="Group ID"),
    user_id: int = typer.Argument(..., help="User ID to promote"),
    title: Optional[str] = typer.Option(None, "--title", help="Admin title"),
    privileges: Optional[str] = typer.Option(
        None, "--privileges", help="Comma-separated privileges: change_info,post,edit,delete,ban,invite,pin,video,anon"
    ),
):
    """Promote a user to admin."""
    from tgops.models.admin import AdminPrivileges
    from tgops.utils.formatting import print_success

    priv_flags = set((privileges or "").split(","))

    privs = AdminPrivileges(
        can_change_info="change_info" in priv_flags,
        can_post_messages="post" in priv_flags,
        can_edit_messages="edit" in priv_flags,
        can_delete_messages="delete" in priv_flags,
        can_ban_users="ban" in priv_flags,
        can_invite_users="invite" in priv_flags or not privileges,
        can_pin_messages="pin" in priv_flags,
        can_manage_video_chats="video" in priv_flags,
        is_anonymous="anon" in priv_flags,
    )

    async def _run():
        from tgops.services.admin import AdminService
        client = _make_client()
        await client.start()
        svc = AdminService(client, get_settings())
        record = await svc.add(group_id, user_id, title, privs)
        await client.stop()
        print_success(f"User {user_id} promoted to admin in group {group_id}.")

    run(_run())


@admin_app.command("remove")
def admin_remove(
    group_id: int = typer.Argument(..., help="Group ID"),
    user_id: int = typer.Argument(..., help="User ID to demote"),
):
    """Demote an admin back to regular member."""
    from tgops.utils.formatting import print_success

    async def _run():
        from tgops.services.admin import AdminService
        client = _make_client()
        await client.start()
        svc = AdminService(client, get_settings())
        await svc.remove(group_id, user_id)
        await client.stop()
        print_success(f"User {user_id} demoted in group {group_id}.")

    run(_run())


@admin_app.command("export")
def admin_export(
    group_id: int = typer.Argument(..., help="Group ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output CSV path"),
):
    """Export admin roster to CSV."""
    from tgops.utils.formatting import print_success

    async def _run():
        from tgops.services.admin import AdminService
        client = _make_client()
        await client.start()
        svc = AdminService(client, get_settings())
        rows = await svc.export(group_id)
        await client.stop()

        if not rows:
            console.print("[yellow]No admins found.[/]")
            return

        if output:
            with open(output, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print_success(f"Admin roster exported to {output}")
        else:
            import io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            console.print(buf.getvalue())

    run(_run())


@admin_app.command("sync")
def admin_sync(
    group_id: int = typer.Argument(..., help="Group ID"),
    roster: str = typer.Option(..., "--roster", "-r", help="Path to CSV roster file"),
    remove: bool = typer.Option(False, "--remove", help="Remove admins not in roster"),
):
    """Sync admin roster from a CSV file."""
    from tgops.utils.formatting import print_success

    with open(roster, newline="") as f:
        rows = list(csv.DictReader(f))

    async def _run():
        from tgops.services.admin import AdminService
        client = _make_client()
        await client.start()
        svc = AdminService(client, get_settings())
        summary = await svc.sync(group_id, rows, remove=remove)
        await client.stop()
        console.print_json(json.dumps(summary, indent=2))

    run(_run())


# ---------------------------------------------------------------------------
# invite commands
# ---------------------------------------------------------------------------

@invite_app.command("rotate")
def invite_rotate(
    group_id: int = typer.Argument(..., help="Group ID"),
):
    """Rotate (revoke + create) the group's invite link."""
    from tgops.utils.formatting import print_success

    async def _run():
        from tgops.services.invite import InviteService
        client = _make_client()
        await client.start()
        svc = InviteService(client, get_settings())
        new_link = await svc.rotate(group_id)
        await client.stop()
        print_success(f"New invite link: {new_link}")

    run(_run())


@invite_app.command("status")
def invite_status(
    group_id: int = typer.Argument(..., help="Group ID"),
):
    """Show current invite link info for a group."""
    async def _run():
        from tgops.services.invite import InviteService
        client = _make_client()
        await client.start()
        svc = InviteService(client, get_settings())
        info = await svc.status(group_id)
        await client.stop()
        console.print_json(json.dumps(info, indent=2))

    run(_run())


# ---------------------------------------------------------------------------
# member commands
# ---------------------------------------------------------------------------

@member_app.command("find")
def member_find(
    user_id: int = typer.Argument(..., help="Telegram user ID"),
):
    """Scan all groups and show a user's membership status."""
    from tgops.utils.formatting import make_table

    async def _run():
        from tgops.services.member import MemberService
        client = _make_client()
        await client.start()
        svc = MemberService(client, get_settings())
        record = await svc.find(user_id)
        await client.stop()

        rows = [
            [str(gid), str(record.is_active.get(gid, False)), str(record.is_admin.get(gid, False))]
            for gid in record.groups
        ]
        name = f"{record.first_name} {record.last_name or ''}".strip() or str(user_id)
        table = make_table(
            f"Member: {name} (@{record.username or 'N/A'})",
            ["Group ID", "Active", "Admin"],
            rows,
        )
        console.print(table)

    run(_run())


@member_app.command("offboard")
def member_offboard(
    user_id: int = typer.Argument(..., help="Telegram user ID"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to send before removing"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip confirmation"),
):
    """Remove a user from all managed groups (planned mode)."""
    from tgops.models.member import OffboardingMode
    from tgops.utils.formatting import print_info, print_offboarding_status, print_warning

    if not no_confirm:
        print_warning(f"About to offboard user {user_id} from all managed groups.")
        confirmed = typer.confirm("Proceed?")
        if not confirmed:
            print_info("Aborted.")
            raise typer.Exit(0)

    async def _run():
        from tgops.services.member import MemberService
        client = _make_client()
        await client.start()
        svc = MemberService(client, get_settings())
        job = await svc.offboard(user_id, message=message, mode=OffboardingMode.PLANNED)
        await client.stop()
        print_offboarding_status(job)

    run(_run())


@member_app.command("emergency")
def member_emergency(
    user_id: int = typer.Argument(..., help="Telegram user ID"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to send before removing"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip confirmation"),
):
    """EMERGENCY removal — minimal delays + rotate all invite links."""
    from tgops.models.member import OffboardingMode
    from tgops.utils.formatting import print_info, print_offboarding_status, print_warning

    console.print("[bold red]WARNING: EMERGENCY MODE[/]")
    console.print("This will remove the user with minimal delays and rotate ALL invite links.")
    console.print("[yellow]Flood risk: high. Proceed with caution.[/]")

    if not no_confirm:
        confirmed = typer.confirm("Proceed with emergency offboarding?")
        if not confirmed:
            print_info("Aborted.")
            raise typer.Exit(0)

    async def _run():
        from tgops.services.member import MemberService
        client = _make_client()
        await client.start()
        svc = MemberService(client, get_settings())
        job = await svc.offboard(user_id, message=message, mode=OffboardingMode.EMERGENCY)
        await client.stop()
        print_offboarding_status(job)

    run(_run())


@member_app.command("ban")
def member_ban(
    user_id: int = typer.Argument(..., help="Telegram user ID"),
    groups: Optional[str] = typer.Option(
        None, "--groups", "-g", help="Comma-separated group IDs (default: all)"
    ),
):
    """Ban a user from specified groups (or all managed groups)."""
    from tgops.utils.formatting import print_offboarding_status

    group_ids = None
    if groups:
        group_ids = [int(g.strip()) for g in groups.split(",") if g.strip()]

    async def _run():
        from tgops.services.member import MemberService
        client = _make_client()
        await client.start()
        svc = MemberService(client, get_settings())
        job = await svc.ban(user_id, group_ids=group_ids)
        await client.stop()
        print_offboarding_status(job)

    run(_run())


@member_app.command("status")
def member_status(
    job_id: str = typer.Argument(..., help="Offboarding job ID"),
):
    """Show the status of an offboarding job."""
    from tgops.utils.formatting import print_offboarding_status

    async def _run():
        from tgops.services.member import MemberService
        client = _make_client()
        svc = MemberService(client, get_settings())
        job = await svc.load_job(job_id)
        print_offboarding_status(job)

    run(_run())


# ---------------------------------------------------------------------------
# serve command (Phase 5 REST API)
# ---------------------------------------------------------------------------

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to listen on"),
    ctx: typer.Context = typer.Argument(default=None),
):
    """Start the REST API server (Phase 5). Requires fastapi and uvicorn."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: pip install uvicorn[standard][/red]")
        raise typer.Exit(1)

    console.print(f"[green]Starting TGOps API on {host}:{port}[/green]")
    console.print("[dim]API docs at /docs[/dim]")
    uvicorn.run("api.main:app", host=host, port=port, reload=False)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
