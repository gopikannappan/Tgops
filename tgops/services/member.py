"""Cross-group member offboarding service."""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any

import aiofiles

from tgops.core.audit import AuditEntry, AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.core.exceptions import MemberIsOwnerError, TGOpsError
from tgops.models.member import MemberRecord, OffboardingJob, OffboardingMode
from tgops.utils.rate_limiter import emergency_delay, human_delay
from tgops.utils.webhook import send_alert

logger = logging.getLogger(__name__)


def _serialize_offboarding_job(job: OffboardingJob) -> dict[str, Any]:
    d = asdict(job)
    d["mode"] = job.mode.value
    d["created_at"] = job.created_at.isoformat()
    d["completed_at"] = job.completed_at.isoformat() if job.completed_at else None
    return d


def _deserialize_offboarding_job(data: dict[str, Any]) -> OffboardingJob:
    data = dict(data)
    data["mode"] = OffboardingMode(data["mode"])
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    if data.get("completed_at"):
        data["completed_at"] = datetime.fromisoformat(data["completed_at"])
    return OffboardingJob(**data)


class MemberService:
    """Cross-group member lookup and offboarding."""

    def __init__(self, client: TGOpsClient, settings: Settings):
        self._client = client
        self._settings = settings
        self._audit = AuditLogger(settings.audit_log_path)
        os.makedirs(os.path.expanduser(settings.offboarding_dir), exist_ok=True)

    def _job_path(self, job_id: str) -> str:
        return os.path.join(
            os.path.expanduser(self._settings.offboarding_dir), f"{job_id}.json"
        )

    async def _save_job(self, job: OffboardingJob) -> None:
        path = self._job_path(job.job_id)
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            await f.write(json.dumps(_serialize_offboarding_job(job), indent=2))

    async def load_job(self, job_id: str) -> OffboardingJob:
        path = self._job_path(job_id)
        if not os.path.exists(path):
            raise TGOpsError(f"Offboarding job file not found: {path}")
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        return _deserialize_offboarding_job(data)

    async def _get_managed_groups(self) -> list[int]:
        """Return a list of all group/supergroup IDs the account is a member of."""
        group_ids = []
        async for dialog in self._client.client.get_dialogs():
            if dialog.chat and dialog.chat.type.name in ("GROUP", "SUPERGROUP"):
                group_ids.append(dialog.chat.id)
        return group_ids

    async def find(self, user_id: int) -> MemberRecord:
        """
        Scan all managed groups and return a MemberRecord showing
        per-group membership, admin status, and active/departed state.
        """
        group_ids = await self._get_managed_groups()
        record = MemberRecord(
            user_id=user_id,
            username=None,
            first_name="",
            last_name=None,
        )

        for gid in group_ids:
            try:
                member = await self._client.call("get_chat_member", gid, user_id)
                user = getattr(member, "user", None)
                if user:
                    record.username = getattr(user, "username", None)
                    record.first_name = getattr(user, "first_name", "") or ""
                    record.last_name = getattr(user, "last_name", None)

                status_name = getattr(getattr(member, "status", None), "name", "").upper()
                is_active = status_name in ("MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR")
                is_admin = status_name in ("ADMINISTRATOR", "ADMIN", "OWNER", "CREATOR")

                record.groups.append(gid)
                record.is_active[gid] = is_active
                record.is_admin[gid] = is_admin
            except Exception:
                # Member not in this group — skip silently
                pass

        return record

    async def offboard(
        self,
        user_id: int,
        message: str | None = None,
        mode: OffboardingMode = OffboardingMode.PLANNED,
    ) -> OffboardingJob:
        """
        Remove user from all groups.

        PLANNED mode: human-like delays between removals.
        EMERGENCY mode: minimal delays + rotate all invite links afterward.
        """
        notify_msg = message or self._settings.default_offboard_message or None

        job = OffboardingJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            username=None,
            mode=mode,
            notify_message=notify_msg,
            status="RUNNING",
        )

        await self._audit.log(
            AuditEntry(
                event="member.offboard.start",
                user_id=user_id,
                details={"mode": mode.value},
            )
        )

        # Find the member first
        record = await self.find(user_id)
        job.username = record.username
        job.groups_found = list(record.groups)
        await self._save_job(job)

        delay_fn = emergency_delay if mode == OffboardingMode.EMERGENCY else human_delay
        delay_base = (
            self._settings.emergency_delay_seconds
            if mode == OffboardingMode.EMERGENCY
            else self._settings.base_delay_seconds
        )

        for gid in record.groups:
            if not record.is_active.get(gid, False):
                job.groups_skipped.append(gid)
                continue

            if self._settings.dry_run:
                logger.info("[DRY RUN] Would remove user %d from group %d", user_id, gid)
                job.groups_removed.append(gid)
                continue

            try:
                # Demote from admin first if needed
                if record.is_admin.get(gid, False):
                    try:
                        from hydrogram.types import ChatPrivileges

                        empty = ChatPrivileges(
                            can_change_info=False,
                            can_post_messages=False,
                            can_edit_messages=False,
                            can_delete_messages=False,
                            can_ban_users=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_manage_video_chats=False,
                            is_anonymous=False,
                        )
                        await self._client.call(
                            "promote_chat_member", gid, user_id=user_id, privileges=empty
                        )
                        await delay_fn(delay_base)
                    except MemberIsOwnerError:
                        logger.warning(
                            "User %d is owner of group %d — cannot remove.", user_id, gid
                        )
                        job.groups_skipped.append(gid)
                        continue
                    except Exception as exc:
                        logger.warning("Failed to demote user %d in group %d: %s", user_id, gid, exc)

                # Send optional notification before removing
                if notify_msg:
                    try:
                        await self._client.call("send_message", user_id, notify_msg)
                        await delay_fn(delay_base)
                    except Exception as exc:
                        logger.warning("Could not send offboard message to user %d: %s", user_id, exc)

                await self._client.call("ban_chat_member", gid, user_id)
                # Immediately unban so we just kick (not permanent ban)
                await self._client.call("unban_chat_member", gid, user_id)
                job.groups_removed.append(gid)
                await delay_fn(delay_base)

            except Exception as exc:
                logger.error("Failed to remove user %d from group %d: %s", user_id, gid, exc)
                job.groups_failed.append(gid)

        # Emergency: rotate invite links for all affected groups
        if mode == OffboardingMode.EMERGENCY and self._settings.emergency_rotate_invites:
            from tgops.services.invite import InviteService

            invite_svc = InviteService(self._client, self._settings)
            await invite_svc.rotate_all(job.groups_found)

            if self._settings.webhook_url:
                await send_alert(
                    self._settings.webhook_url,
                    self._settings.webhook_type,
                    f"EMERGENCY offboarding completed for user {user_id}. "
                    f"Removed from {len(job.groups_removed)} groups. "
                    f"Invite links rotated.",
                )

        job.status = "COMPLETE"
        job.completed_at = datetime.utcnow()
        await self._save_job(job)
        await self._audit.log(
            AuditEntry(
                event="member.offboard.complete",
                user_id=user_id,
                status="COMPLETE",
                details={
                    "mode": mode.value,
                    "groups_removed": len(job.groups_removed),
                    "groups_skipped": len(job.groups_skipped),
                    "groups_failed": len(job.groups_failed),
                },
            )
        )

        return job

    async def ban(
        self,
        user_id: int,
        group_ids: list[int] | None = None,
    ) -> OffboardingJob:
        """Ban user from specified groups (or all managed groups if None)."""
        if group_ids is None:
            group_ids = await self._get_managed_groups()

        job = OffboardingJob(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            username=None,
            mode=OffboardingMode.PLANNED,
            status="RUNNING",
        )
        job.groups_found = list(group_ids)
        await self._save_job(job)

        for gid in group_ids:
            if self._settings.dry_run:
                logger.info("[DRY RUN] Would ban user %d from group %d", user_id, gid)
                job.groups_removed.append(gid)
                continue

            try:
                await self._client.call("ban_chat_member", gid, user_id)
                job.groups_removed.append(gid)
                await human_delay(self._settings.base_delay_seconds)
            except Exception as exc:
                logger.error("Failed to ban user %d from group %d: %s", user_id, gid, exc)
                job.groups_failed.append(gid)

        job.status = "COMPLETE"
        job.completed_at = datetime.utcnow()
        await self._save_job(job)
        await self._audit.log(
            AuditEntry(
                event="member.ban.complete",
                user_id=user_id,
                status="COMPLETE",
                details={
                    "groups_banned": len(job.groups_removed),
                    "groups_failed": len(job.groups_failed),
                },
            )
        )
        return job
