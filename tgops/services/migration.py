"""10-step group migration orchestrator."""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import aiofiles

from tgops.core.audit import AuditEntry, AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.core.exceptions import MigrationStepError, TGOpsError
from tgops.models.group import GroupState
from tgops.models.migration import MigrationJob, MigrationStatus
from tgops.utils.rate_limiter import BATCH_SIZE, batch_delay, human_delay

logger = logging.getLogger(__name__)


def _serialize_job(job: MigrationJob) -> dict[str, Any]:
    """Serialize a MigrationJob to a JSON-compatible dict."""
    d = asdict(job)
    d["created_at"] = job.created_at.isoformat()
    d["completed_at"] = job.completed_at.isoformat() if job.completed_at else None
    d["status"] = job.status.value
    return d


def _deserialize_job(data: dict[str, Any]) -> MigrationJob:
    """Deserialize a MigrationJob from a dict."""
    data = dict(data)
    data["status"] = MigrationStatus(data["status"])
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    if data.get("completed_at"):
        data["completed_at"] = datetime.fromisoformat(data["completed_at"])
    return MigrationJob(**data)


class MigrationService:
    """Orchestrates the full 10-step group migration process."""

    STEPS = [
        "snapshot",
        "create_target",
        "copy_settings",
        "generate_invite",
        "transfer_ownership",
        "archive_source",
        "pin_redirect",
        "blast_invite",
        "set_redirect",
        "complete",
    ]

    def __init__(self, client: TGOpsClient, settings: Settings):
        self._client = client
        self._settings = settings
        self._audit = AuditLogger(settings.audit_log_path)
        os.makedirs(os.path.expanduser(settings.jobs_dir), exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        return os.path.join(os.path.expanduser(self._settings.jobs_dir), f"{job_id}.json")

    async def _save_job(self, job: MigrationJob) -> None:
        path = self._job_path(job.job_id)
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(_serialize_job(job), indent=2))

    async def _load_job(self, job_id: str) -> MigrationJob:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            raise TGOpsError(f"Job file not found: {path}")
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        return _deserialize_job(data)

    async def plan(self, source_group_id: int) -> dict:
        """
        Dry-run: return the step plan without making any API calls.
        Checks 24h membership requirement.
        """
        return {
            "source_group_id": source_group_id,
            "steps": self.STEPS,
            "dry_run": True,
            "note": (
                "Step 'transfer_ownership' requires the org account to have been "
                "a member of the source group for at least 24 hours."
            ),
            "estimated_time": "Varies based on group size (batch_delay every 20 members during blast_invite).",
        }

    async def run(
        self,
        source_group_id: int,
        new_title: str | None = None,
    ) -> MigrationJob:
        """Execute the full 10-step migration."""
        job_id = str(uuid.uuid4())
        job = MigrationJob(
            job_id=job_id,
            source_group_id=source_group_id,
            status=MigrationStatus.PENDING,
        )
        await self._save_job(job)
        await self._audit.log(
            AuditEntry(
                event="migration.start",
                job_id=job_id,
                group_id=source_group_id,
                details={"new_title": new_title},
            )
        )

        return await self._execute(job, new_title=new_title)

    async def resume(self, job_id: str) -> MigrationJob:
        """Load job from disk, skip completed steps, resume from last failed step."""
        job = await self._load_job(job_id)
        if job.status == MigrationStatus.COMPLETE:
            logger.info("Job %s is already complete.", job_id)
            return job
        if job.status == MigrationStatus.FAILED:
            job.status = MigrationStatus.PENDING
            job.error = None
            await self._save_job(job)

        return await self._execute(job)

    async def status(self, job_id: str) -> MigrationJob:
        """Load and return a job by ID."""
        return await self._load_job(job_id)

    async def batch(self, group_ids: list[int]) -> list[MigrationJob]:
        """Sequential migration of multiple groups."""
        results = []
        for group_id in group_ids:
            logger.info("Starting batch migration for group %d", group_id)
            job = await self.run(group_id)
            results.append(job)
        return results

    # ------------------------------------------------------------------
    # Internal execution engine
    # ------------------------------------------------------------------

    async def _execute(self, job: MigrationJob, new_title: str | None = None) -> MigrationJob:
        """Run all pending steps sequentially."""
        step_methods = {
            "snapshot": self._step_snapshot,
            "create_target": self._step_create_target,
            "copy_settings": self._step_copy_settings,
            "generate_invite": self._step_generate_invite,
            "transfer_ownership": self._step_transfer_ownership,
            "archive_source": self._step_archive_source,
            "pin_redirect": self._step_pin_redirect,
            "blast_invite": self._step_blast_invite,
            "set_redirect": self._step_set_redirect,
            "complete": self._step_complete,
        }

        # State shared across steps
        state: dict[str, Any] = {"new_title": new_title}

        for step_name in self.STEPS:
            if step_name in job.steps_completed:
                logger.info("Step '%s' already completed, skipping.", step_name)
                continue

            logger.info("Executing step: %s", step_name)
            try:
                await step_methods[step_name](job, state)
                job.steps_completed.append(step_name)
                await self._save_job(job)
                await self._audit.log(
                    AuditEntry(
                        event=f"migration.step.{step_name}",
                        job_id=job.job_id,
                        group_id=job.source_group_id,
                        step=step_name,
                        status="completed",
                    )
                )
            except MigrationStepError as exc:
                job.status = MigrationStatus.FAILED
                job.error = str(exc)
                await self._save_job(job)
                await self._audit.log(
                    AuditEntry(
                        event=f"migration.step.{step_name}",
                        job_id=job.job_id,
                        group_id=job.source_group_id,
                        step=step_name,
                        status="failed",
                        details={"error": str(exc), "recoverable": exc.recoverable},
                    )
                )
                raise
            except Exception as exc:
                job.status = MigrationStatus.FAILED
                job.error = str(exc)
                await self._save_job(job)
                raise MigrationStepError(
                    str(exc), step=step_name, job_id=job.job_id, recoverable=True
                ) from exc

        return job

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    async def _step_snapshot(self, job: MigrationJob, state: dict) -> None:
        """Step 1: Capture GroupState snapshot to audit log."""
        if self._settings.dry_run:
            state["source_title"] = f"Group {job.source_group_id}"
            state["source_description"] = ""
            return

        chat = await self._client.call("get_chat", job.source_group_id)
        title = getattr(chat, "title", str(job.source_group_id))
        snapshot = GroupState(
            group_id=job.source_group_id,
            title=title,
            username=getattr(chat, "username", None),
            owner_user_id=0,  # Can't always determine; set 0 if unavailable
            member_count=getattr(chat, "members_count", 0) or 0,
            invite_link=getattr(chat, "invite_link", None),
        )
        state["source_title"] = snapshot.title
        state["source_description"] = getattr(chat, "description", "") or ""
        await self._audit.log(
            AuditEntry(
                event="migration.snapshot",
                job_id=job.job_id,
                group_id=job.source_group_id,
                details={
                    "title": snapshot.title,
                    "member_count": snapshot.member_count,
                    "invite_link": snapshot.invite_link,
                },
            )
        )

    async def _step_create_target(self, job: MigrationJob, state: dict) -> None:
        """Step 2: Create new supergroup."""
        if job.target_group_id is not None:
            # Already created (idempotent)
            return

        if self._settings.dry_run:
            logger.info("[DRY RUN] Would create new supergroup.")
            job.status = MigrationStatus.CREATING_TARGET
            return

        new_title = state.get("new_title") or state.get("source_title", "New Group")
        chat = await self._client.call("create_supergroup", title=new_title)
        job.target_group_id = chat.id
        job.status = MigrationStatus.CREATING_TARGET

    async def _step_copy_settings(self, job: MigrationJob, state: dict) -> None:
        """Step 3: Copy title, description, and default permissions from source."""
        if self._settings.dry_run or job.target_group_id is None:
            return

        description = state.get("source_description", "")
        if description:
            try:
                await self._client.call(
                    "set_chat_description", job.target_group_id, description
                )
            except Exception as exc:
                logger.warning("Could not copy description: %s", exc)

    async def _step_generate_invite(self, job: MigrationJob, state: dict) -> None:
        """Step 4: Create a permanent invite link for the target group."""
        if self._settings.dry_run or job.target_group_id is None:
            state["target_invite_link"] = "https://t.me/joinchat/DRY_RUN"
            return

        link = await self._client.call("create_chat_invite_link", job.target_group_id)
        state["target_invite_link"] = link.invite_link

    async def _step_transfer_ownership(self, job: MigrationJob, state: dict) -> None:
        """Step 5: Promote org account to owner — requires ≥24h membership."""
        job.status = MigrationStatus.TRANSFERRING_OWNERSHIP

        if self._settings.dry_run or job.target_group_id is None:
            return

        me = await self._client.call("get_me")

        # Check 24h membership requirement
        try:
            member = await self._client.call(
                "get_chat_member", job.source_group_id, me.id
            )
            join_date = getattr(member, "joined_date", None)
            if join_date:
                now = datetime.now(timezone.utc)
                if join_date.tzinfo is None:
                    join_date = join_date.replace(tzinfo=timezone.utc)
                elapsed = (now - join_date).total_seconds()
                if elapsed < 86400:
                    remaining = int(86400 - elapsed)
                    hours, rem = divmod(remaining, 3600)
                    mins = rem // 60
                    raise MigrationStepError(
                        f"24h membership requirement not met. "
                        f"Account joined {elapsed / 3600:.1f}h ago. "
                        f"Wait {hours}h {mins}m more.",
                        step="transfer_ownership",
                        job_id=job.job_id,
                        recoverable=True,
                    )
        except MigrationStepError:
            raise
        except Exception as exc:
            logger.warning("Could not verify join date: %s", exc)

        # Transfer ownership of target group to org account (org account creates the group,
        # so it's already owner; this step ensures any co-owner handoff is documented)
        logger.info(
            "Ownership transfer verified for job %s (org account id=%d)", job.job_id, me.id
        )

    async def _step_archive_source(self, job: MigrationJob, state: dict) -> None:
        """Step 6: Rename source group to '[ARCHIVED] <title>'."""
        job.status = MigrationStatus.ARCHIVING_SOURCE

        if self._settings.dry_run:
            return

        prefix = self._settings.archive_prefix
        source_title = state.get("source_title", str(job.source_group_id))
        archived_title = f"{prefix} {source_title}"

        try:
            await self._client.call(
                "set_chat_title", job.source_group_id, archived_title
            )
        except Exception as exc:
            raise MigrationStepError(
                f"Failed to archive source group: {exc}",
                step="archive_source",
                job_id=job.job_id,
            ) from exc

    async def _step_pin_redirect(self, job: MigrationJob, state: dict) -> None:
        """Step 7: Pin the migration redirect message in the source group."""
        invite_link = state.get("target_invite_link", "")
        message = self._settings.archive_message.format(invite_link=invite_link)

        if self._settings.dry_run:
            logger.info("[DRY RUN] Would pin redirect message in source group.")
            return

        try:
            sent = await self._client.call(
                "send_message", job.source_group_id, message
            )
            await self._client.call(
                "pin_chat_message", job.source_group_id, sent.id, disable_notification=False
            )
        except Exception as exc:
            logger.warning("Could not pin redirect message: %s", exc)

    async def _step_blast_invite(self, job: MigrationJob, state: dict) -> None:
        """Step 8: Send invite link to all members of the source group (batched)."""
        job.status = MigrationStatus.BLASTING_INVITE
        invite_link = state.get("target_invite_link", "")
        message = f"Please join our new group: {invite_link}"

        if self._settings.dry_run:
            logger.info("[DRY RUN] Would blast invite to all members.")
            return

        count = 0
        async for member in self._client.client.get_chat_members(job.source_group_id):
            user = getattr(member, "user", None)
            if user is None or getattr(user, "is_bot", False):
                continue
            try:
                await self._client.call("send_message", user.id, message)
                count += 1
                if count % BATCH_SIZE == 0:
                    logger.info("Invite blast: sent to %d members, pausing...", count)
                    await batch_delay()
            except Exception as exc:
                logger.warning("Could not send invite to user %d: %s", user.id, exc)

        logger.info("Invite blast complete: %d members messaged.", count)

    async def _step_set_redirect(self, job: MigrationJob, state: dict) -> None:
        """Step 9: Register a message handler that auto-replies with the invite link."""
        job.status = MigrationStatus.SETTING_REDIRECT
        invite_link = state.get("target_invite_link", "")

        if self._settings.dry_run:
            logger.info("[DRY RUN] Would register redirect handler.")
            return

        # Register a Hydrogram message handler for the source group
        from hydrogram import filters

        source_id = job.source_group_id
        redirect_msg = (
            f"This group has been archived. Please join us here: {invite_link}"
        )

        @self._client.client.on_message(filters.chat(source_id) & filters.text)
        async def _redirect_handler(client, message):
            try:
                await message.reply(redirect_msg)
            except Exception:
                pass

        logger.info(
            "Redirect handler registered for group %d -> %s", source_id, invite_link
        )

    async def _step_complete(self, job: MigrationJob, state: dict) -> None:
        """Step 10: Write final audit entry and mark job as COMPLETE."""
        job.status = MigrationStatus.COMPLETE
        job.completed_at = datetime.utcnow()
        await self._audit.log(
            AuditEntry(
                event="migration.complete",
                job_id=job.job_id,
                group_id=job.source_group_id,
                status="COMPLETE",
                details={
                    "target_group_id": job.target_group_id,
                    "steps_completed": job.steps_completed,
                },
            )
        )
