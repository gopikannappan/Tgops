"""Invite link lifecycle management service."""

from __future__ import annotations

import logging

from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.core.exceptions import TGOpsError

logger = logging.getLogger(__name__)


class InviteService:
    """Manage Telegram invite links for groups."""

    def __init__(self, client: TGOpsClient, settings: Settings):
        self._client = client
        self._settings = settings

    async def rotate(self, group_id: int) -> str:
        """
        Revoke the current invite link and create a new one.

        Returns the new permanent invite link URL.
        """
        if self._settings.dry_run:
            logger.info("[DRY RUN] Would rotate invite link for group %d", group_id)
            return "https://t.me/joinchat/DRY_RUN_LINK"

        try:
            # Revoke existing invite links
            await self._client.call("revoke_chat_invite_link", group_id)
        except Exception as exc:
            logger.warning("Could not revoke existing invite link: %s", exc)

        try:
            link = await self._client.call("create_chat_invite_link", group_id)
            return link.invite_link
        except Exception as exc:
            raise TGOpsError(f"Failed to create invite link for group {group_id}: {exc}") from exc

    async def status(self, group_id: int) -> dict:
        """
        Return information about the group's current invite link.

        Returns a dict with: group_id, invite_link, member_count, title.
        """
        try:
            chat = await self._client.call("get_chat", group_id)
            return {
                "group_id": group_id,
                "title": getattr(chat, "title", str(group_id)),
                "invite_link": getattr(chat, "invite_link", None),
                "member_count": getattr(chat, "members_count", None),
                "username": getattr(chat, "username", None),
            }
        except Exception as exc:
            raise TGOpsError(f"Failed to get invite status for group {group_id}: {exc}") from exc

    async def rotate_all(self, group_ids: list[int]) -> dict[int, str]:
        """
        Rotate invite links for all specified groups.

        Returns a mapping of group_id -> new invite link.
        """
        results: dict[int, str] = {}
        for group_id in group_ids:
            try:
                new_link = await self.rotate(group_id)
                results[group_id] = new_link
                logger.info("Rotated invite link for group %d -> %s", group_id, new_link)
            except TGOpsError as exc:
                logger.error("Failed to rotate invite for group %d: %s", group_id, exc)
                results[group_id] = ""
        return results
