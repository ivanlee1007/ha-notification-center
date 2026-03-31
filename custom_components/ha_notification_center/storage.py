"""Storage manager for Notification Center snooze/repeat/acknowledge state."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


class NotificationStorage:
    """Manage notification state storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize storage."""
        self._hass = hass
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict[str, Any] = {
            "snooze_map": {},
            "repeat_map": {},
            "acknowledge_map": {},
        }

    async def async_load(self) -> None:
        """Load data from store."""
        stored = await self._store.async_load()
        if stored:
            self._data.update(stored)

    async def async_save(self) -> None:
        """Save data to store."""
        await self._store.async_save(self._data)

    # --- Snooze ---

    async def async_set_snooze(self, source_id: str, hours: int) -> None:
        """Snooze a notification source for given hours."""
        until = (datetime.now() + timedelta(hours=hours)).isoformat()
        self._data["snooze_map"][source_id] = until
        await self.async_save()

    async def async_remove_snooze(self, source_id: str) -> None:
        """Remove snooze from a source."""
        self._data["snooze_map"].pop(source_id, None)
        await self.async_save()

    async def async_is_snoozed(self, source_id: str) -> bool:
        """Check if a source is snoozed."""
        until_str = self._data["snooze_map"].get(source_id)
        if not until_str:
            return False
        try:
            until = datetime.fromisoformat(until_str)
            if datetime.now() < until:
                return True
            # Expired - clean up
            del self._data["snooze_map"][source_id]
            await self.async_save()
            return False
        except (ValueError, TypeError):
            return False

    # --- Acknowledge ---

    async def async_acknowledge(self, source_id: str) -> None:
        """Acknowledge a notification."""
        self._data["acknowledge_map"][source_id] = datetime.now().isoformat()
        await self.async_save()

    async def is_acknowledged(self, source_id: str) -> bool:
        """Check if a source has been acknowledged."""
        return source_id in self._data.get("acknowledge_map", {})

    # --- Repeat ---

    async def async_set_last_repeat(self, source_id: str) -> None:
        """Record last repeat time."""
        self._data["repeat_map"][source_id] = datetime.now().isoformat()
        await self.async_save()

    async def should_repeat(self, source_id: str, interval_minutes: int) -> bool:
        """Check if a critical notification should be repeated."""
        last_str = self._data["repeat_map"].get(source_id)
        if not last_str:
            return True
        try:
            last = datetime.fromisoformat(last_str)
            return datetime.now() >= last + timedelta(minutes=interval_minutes)
        except (ValueError, TypeError):
            return True

    # --- Cleanup ---

    async def async_cleanup_expired(self) -> None:
        """Clean up expired snooze entries."""
        now = datetime.now()
        expired = [
            sid
            for sid, until_str in list(self._data["snooze_map"].items())
            if datetime.fromisoformat(until_str) < now
        ]
        for sid in expired:
            del self._data["snooze_map"][sid]
        if expired:
            await self.async_save()
