"""Admin record model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AdminPrivileges:
    """Telegram admin privilege flags."""

    can_change_info: bool = False
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_ban_users: bool = False
    can_invite_users: bool = True
    can_pin_messages: bool = False
    can_manage_video_chats: bool = False
    is_anonymous: bool = False


@dataclass
class AdminRecord:
    """Record of an admin assignment in a group."""

    user_id: int
    username: str | None
    group_id: int
    privileges: AdminPrivileges
    added_by: int
    added_at: datetime
    removed_at: datetime | None = None
