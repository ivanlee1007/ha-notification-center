"""Binary sensor platform for Notification Center."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_PRIORITY,
    DOMAIN,
    PRIORITY_CRITICAL,
    PRIORITY_WARNING,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Set up binary sensor entities."""
    async_add_entities(
        [
            NotificationAnyActiveSensor(hass),
            NotificationAnyCriticalSensor(hass),
            NotificationAnyWarningSensor(hass),
        ]
    )


class NotificationAnyActiveSensor(BinarySensorEntity):
    """Binary sensor: any notification is active."""

    _attr_name = "Notification Any Active"
    _attr_unique_id = "ha_notification_center_any_active"
    _attr_icon = "mdi:bell"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        self._hass = hass

    @property
    def is_on(self) -> bool:
        """Return True if any notification is active."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        return len(active) > 0


class NotificationAnyCriticalSensor(BinarySensorEntity):
    """Binary sensor: any critical notification is active."""

    _attr_name = "Notification Any Critical"
    _attr_unique_id = "ha_notification_center_any_critical"
    _attr_icon = "mdi:alert-circle"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        self._hass = hass

    @property
    def is_on(self) -> bool:
        """Return True if any critical notification is active."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        return any(
            n.get(ATTR_PRIORITY) == PRIORITY_CRITICAL for n in active.values()
        )


class NotificationAnyWarningSensor(BinarySensorEntity):
    """Binary sensor: any warning notification is active."""

    _attr_name = "Notification Any Warning"
    _attr_unique_id = "ha_notification_center_any_warning"
    _attr_icon = "mdi:alert"

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        self._hass = hass

    @property
    def is_on(self) -> bool:
        """Return True if any warning notification is active."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        return any(
            n.get(ATTR_PRIORITY) in (PRIORITY_WARNING, PRIORITY_CRITICAL)
            for n in active.values()
        )
