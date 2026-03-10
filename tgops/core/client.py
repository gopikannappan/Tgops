"""Singleton Hydrogram client wrapper with FloodWait handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from hydrogram import Client
from hydrogram.errors import FloodWait

from tgops.core.config import Settings
from tgops.core.exceptions import AuthError, FloodWaitError, TGOpsError
from tgops.utils.rate_limiter import human_delay

logger = logging.getLogger(__name__)


class TGOpsClient:
    """
    Singleton wrapper around hydrogram.Client.

    All Telegram API calls should go through `call()` to get:
    - Automatic human-like delay before each call
    - FloodWait retry with backoff
    - Consistent error wrapping
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Client | None = None
        self._started = False

    def _build_client(self) -> Client:
        import os

        session_path = os.path.expanduser(self._settings.session_path)
        session_dir = os.path.dirname(session_path)
        os.makedirs(session_dir, exist_ok=True)

        return Client(
            name=session_path,
            api_id=self._settings.api_id,
            api_hash=self._settings.api_hash,
            phone_number=self._settings.phone,
        )

    async def start(self) -> None:
        """Initialize and start the Hydrogram client."""
        if self._started:
            return
        if self._client is None:
            self._client = self._build_client()
        try:
            await self._client.start()
            self._started = True
            logger.info("Hydrogram client started successfully.")
        except Exception as exc:
            raise AuthError(f"Failed to start Hydrogram client: {exc}") from exc

    async def stop(self) -> None:
        """Stop the Hydrogram client."""
        if self._client and self._started:
            try:
                await self._client.stop()
            except Exception as exc:
                logger.warning("Error stopping client: %s", exc)
            finally:
                self._started = False

    async def call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call a Hydrogram client method by name.

        Applies human_delay before the call. Retries on FloodWait up to
        max_flood_retries times. Wraps unexpected errors in TGOpsError.
        """
        if not self._started or self._client is None:
            raise TGOpsError("Client is not started. Call start() first.")

        method = getattr(self._client, method_name, None)
        if method is None:
            raise TGOpsError(f"Unknown Hydrogram method: {method_name!r}")

        await human_delay(self._settings.base_delay_seconds)

        last_exc: Exception | None = None
        for attempt in range(self._settings.max_flood_retries + 1):
            try:
                result = method(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            except FloodWait as exc:
                wait_seconds = exc.value
                logger.warning(
                    "FloodWait on %s: waiting %ds (attempt %d/%d)",
                    method_name,
                    wait_seconds,
                    attempt + 1,
                    self._settings.max_flood_retries,
                )
                if attempt < self._settings.max_flood_retries:
                    await asyncio.sleep(wait_seconds)
                    last_exc = exc
                else:
                    raise FloodWaitError(wait_seconds) from exc
            except Exception as exc:
                raise TGOpsError(f"Error calling {method_name}: {exc}") from exc

        # Should not reach here, but satisfy the type checker
        raise FloodWaitError(0)

    @property
    def client(self) -> Client:
        """Direct access to the underlying Hydrogram client (for handler registration)."""
        if self._client is None:
            raise TGOpsError("Client not initialized. Call start() first.")
        return self._client

    async def __aenter__(self) -> "TGOpsClient":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()
