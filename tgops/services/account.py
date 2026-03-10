"""Account bootstrap and verification service."""

from __future__ import annotations

import logging

from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.core.exceptions import AuthError

logger = logging.getLogger(__name__)


class AccountService:
    """Manages Telegram account authentication and session lifecycle."""

    def __init__(self, client: TGOpsClient, settings: Settings):
        self._client = client
        self._settings = settings

    async def setup(self) -> None:
        """
        Interactive OTP wizard.

        Starts the client (Hydrogram handles the OTP prompt natively when
        the session doesn't exist yet). Prints status using Rich after success.
        """
        from tgops.utils.formatting import console, print_info, print_success

        print_info(f"Starting account setup for {self._settings.phone} ...")
        print_info(f"Session will be saved to: {self._settings.session_path}")

        # Hydrogram will interactively prompt for the OTP when needed
        await self._client.start()

        me = await self._client.call("get_me")
        print_success(f"Authenticated as: {me.first_name} (id={me.id})")

    async def status(self) -> dict:
        """
        Return a status dict with account information.

        Keys: phone, session_path, is_authorized, me, group_count.
        """
        import os

        session_file = self._settings.session_path + ".session"
        session_exists = os.path.isfile(session_file)

        result: dict = {
            "phone": self._settings.phone,
            "session_path": self._settings.session_path,
            "is_authorized": False,
            "me": None,
            "group_count": 0,
        }

        if not session_exists:
            return result

        try:
            if not self._client._started:
                await self._client.start()

            me = await self._client.call("get_me")
            result["is_authorized"] = True
            result["me"] = {
                "id": me.id,
                "first_name": me.first_name,
                "last_name": getattr(me, "last_name", None),
                "username": getattr(me, "username", None),
                "phone": getattr(me, "phone_number", None),
            }

            # Count groups/supergroups we're a member of
            count = 0
            async for dialog in self._client.client.get_dialogs():
                if dialog.chat and dialog.chat.type.name in ("GROUP", "SUPERGROUP"):
                    count += 1
            result["group_count"] = count

        except Exception as exc:
            logger.warning("Could not fetch account status: %s", exc)

        return result

    async def verify(self) -> bool:
        """
        Return True if the current session is valid, False if re-auth is needed.
        """
        import os

        session_file = self._settings.session_path + ".session"
        if not os.path.isfile(session_file):
            return False

        try:
            if not self._client._started:
                await self._client.start()
            me = await self._client.call("get_me")
            return me is not None
        except (AuthError, Exception):
            return False
