"""Admin roster management service."""

from __future__ import annotations

import logging
from datetime import datetime

from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.core.exceptions import GroupNotFoundError, InsufficientPrivilegesError, TGOpsError
from tgops.models.admin import AdminPrivileges, AdminRecord

logger = logging.getLogger(__name__)


class AdminService:
    """Manage admin rosters for Telegram groups."""

    def __init__(self, client: TGOpsClient, settings: Settings):
        self._client = client
        self._settings = settings

    async def list(self, group_id: int) -> list[AdminRecord]:
        """Return the list of current admins for a group."""
        try:
            admins: list[AdminRecord] = []
            async for member in self._client.client.get_chat_members(
                group_id, filter="administrators"
            ):
                user = member.user
                privs = self._extract_privileges(member)
                record = AdminRecord(
                    user_id=user.id,
                    username=getattr(user, "username", None),
                    group_id=group_id,
                    privileges=privs,
                    added_by=getattr(member, "invited_by", None) and member.invited_by.id or 0,
                    added_at=getattr(member, "joined_date", datetime.utcnow()) or datetime.utcnow(),
                )
                admins.append(record)
            return admins
        except TGOpsError:
            raise
        except Exception as exc:
            raise TGOpsError(f"Failed to list admins for group {group_id}: {exc}") from exc

    def _extract_privileges(self, member: object) -> AdminPrivileges:
        """Extract AdminPrivileges from a ChatMember object."""
        priv = getattr(member, "privileges", None)
        if priv is None:
            return AdminPrivileges()
        return AdminPrivileges(
            can_change_info=getattr(priv, "can_change_info", False),
            can_post_messages=getattr(priv, "can_post_messages", False),
            can_edit_messages=getattr(priv, "can_edit_messages", False),
            can_delete_messages=getattr(priv, "can_delete_messages", False),
            can_ban_users=getattr(priv, "can_ban_users", False),
            can_invite_users=getattr(priv, "can_invite_users", True),
            can_pin_messages=getattr(priv, "can_pin_messages", False),
            can_manage_video_chats=getattr(priv, "can_manage_video_chats", False),
            is_anonymous=getattr(priv, "is_anonymous", False),
        )

    async def add(
        self,
        group_id: int,
        user_id: int,
        title: str | None,
        privileges: AdminPrivileges,
    ) -> AdminRecord:
        """Promote a user to admin with specified privileges."""
        if self._settings.dry_run:
            logger.info("[DRY RUN] Would promote user %d in group %d", user_id, group_id)
            return AdminRecord(
                user_id=user_id,
                username=None,
                group_id=group_id,
                privileges=privileges,
                added_by=0,
                added_at=datetime.utcnow(),
            )

        try:
            from hydrogram.types import ChatPrivileges

            tg_privileges = ChatPrivileges(
                can_change_info=privileges.can_change_info,
                can_post_messages=privileges.can_post_messages,
                can_edit_messages=privileges.can_edit_messages,
                can_delete_messages=privileges.can_delete_messages,
                can_ban_users=privileges.can_ban_users,
                can_invite_users=privileges.can_invite_users,
                can_pin_messages=privileges.can_pin_messages,
                can_manage_video_chats=privileges.can_manage_video_chats,
                is_anonymous=privileges.is_anonymous,
            )

            kwargs: dict = {"user_id": user_id, "privileges": tg_privileges}
            if title:
                kwargs["title"] = title

            await self._client.call("promote_chat_member", group_id, **kwargs)

            me = await self._client.call("get_me")
            return AdminRecord(
                user_id=user_id,
                username=None,
                group_id=group_id,
                privileges=privileges,
                added_by=me.id,
                added_at=datetime.utcnow(),
            )
        except TGOpsError:
            raise
        except Exception as exc:
            raise TGOpsError(f"Failed to add admin {user_id} to group {group_id}: {exc}") from exc

    async def remove(self, group_id: int, user_id: int) -> None:
        """Demote a user from admin status."""
        if self._settings.dry_run:
            logger.info("[DRY RUN] Would demote user %d in group %d", user_id, group_id)
            return

        try:
            from hydrogram.types import ChatPrivileges

            empty_privileges = ChatPrivileges(
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
                "promote_chat_member", group_id, user_id=user_id, privileges=empty_privileges
            )
        except TGOpsError:
            raise
        except Exception as exc:
            raise TGOpsError(f"Failed to remove admin {user_id} from group {group_id}: {exc}") from exc

    async def export(self, group_id: int) -> list[dict]:
        """Return admin records as CSV-ready dicts."""
        admins = await self.list(group_id)
        rows = []
        for a in admins:
            p = a.privileges
            rows.append(
                {
                    "user_id": str(a.user_id),
                    "username": a.username or "",
                    "group_id": str(a.group_id),
                    "added_by": str(a.added_by),
                    "added_at": a.added_at.isoformat(),
                    "removed_at": a.removed_at.isoformat() if a.removed_at else "",
                    "can_change_info": str(p.can_change_info),
                    "can_post_messages": str(p.can_post_messages),
                    "can_edit_messages": str(p.can_edit_messages),
                    "can_delete_messages": str(p.can_delete_messages),
                    "can_ban_users": str(p.can_ban_users),
                    "can_invite_users": str(p.can_invite_users),
                    "can_pin_messages": str(p.can_pin_messages),
                    "can_manage_video_chats": str(p.can_manage_video_chats),
                    "is_anonymous": str(p.is_anonymous),
                }
            )
        return rows

    async def sync(
        self,
        group_id: int,
        roster: list[dict],
        remove: bool = False,
    ) -> dict:
        """
        Sync admin roster from a list of dicts (as produced by export).

        Returns a summary dict: {added: [...], removed: [...], unchanged: [...], errors: [...]}.
        """
        current_admins = await self.list(group_id)
        current_ids = {a.user_id for a in current_admins}
        roster_ids = {int(r["user_id"]) for r in roster}

        summary: dict = {"added": [], "removed": [], "unchanged": [], "errors": []}

        for row in roster:
            uid = int(row["user_id"])
            if uid in current_ids:
                summary["unchanged"].append(uid)
                continue
            try:
                privs = AdminPrivileges(
                    can_change_info=row.get("can_change_info", "False") == "True",
                    can_post_messages=row.get("can_post_messages", "False") == "True",
                    can_edit_messages=row.get("can_edit_messages", "False") == "True",
                    can_delete_messages=row.get("can_delete_messages", "False") == "True",
                    can_ban_users=row.get("can_ban_users", "False") == "True",
                    can_invite_users=row.get("can_invite_users", "True") == "True",
                    can_pin_messages=row.get("can_pin_messages", "False") == "True",
                    can_manage_video_chats=row.get("can_manage_video_chats", "False") == "True",
                    is_anonymous=row.get("is_anonymous", "False") == "True",
                )
                await self.add(group_id, uid, row.get("title"), privs)
                summary["added"].append(uid)
            except Exception as exc:
                summary["errors"].append({"user_id": uid, "error": str(exc)})

        if remove:
            for admin in current_admins:
                if admin.user_id not in roster_ids:
                    try:
                        await self.remove(group_id, admin.user_id)
                        summary["removed"].append(admin.user_id)
                    except Exception as exc:
                        summary["errors"].append({"user_id": admin.user_id, "error": str(exc)})

        return summary
