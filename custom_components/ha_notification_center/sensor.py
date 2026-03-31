"""Sensor platform for Notification Center."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ATTR_DESCRIPTION,
    ATTR_ICON,
    ATTR_NAME,
    ATTR_PRIORITY,
    ATTR_TAP_ACTION_ENTITY,
    ATTR_TIMESTAMP,
    DOMAIN,
    PRIORITY_CRITICAL,
    PRIORITY_WARNING,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    async_add_entities(
        [
            NotificationFeedSensor(hass),
            NotificationCountSensor(hass, "warning"),
            NotificationCountSensor(hass, "critical"),
        ]
    )


class NotificationFeedSensor(SensorEntity):
    """Notification feed sensor - shows active notification count and details."""

    _attr_icon = "mdi:bell"
    _attr_native_value = 0

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        self._hass = hass
        self._attr_name = "Notification Feed"
        self._attr_unique_id = "ha_notification_center_feed"
        self._attr_extra_state_attributes = {}

    @property
    def native_value(self) -> int:
        """Return the count of active notifications."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        return len(active)

    @property
    def extra_state_attributes(self) -> dict:
        """Return notification details."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        notifications = []
        for nid, notif in active.items():
            notifications.append(
                {
                    "source_id": nid,
                    "name": notif.get(ATTR_NAME, nid),
                    "icon": notif.get(ATTR_ICON, "mdi:bell"),
                    "priority": notif.get(ATTR_PRIORITY, "info"),
                    "description": notif.get(ATTR_DESCRIPTION, ""),
                    "tap_action_entity": notif.get(ATTR_TAP_ACTION_ENTITY),
                    "timestamp": notif.get(ATTR_TIMESTAMP, ""),
                    "acknowledged": notif.get("acknowledged", False),
                }
            )
        return {
            "notifications": notifications,
            "count": len(notifications),
        }


class NotificationCountSensor(SensorEntity):
    """Count sensor for specific priority level."""

    _attr_native_value = 0

    def __init__(self, hass: HomeAssistant, priority: str) -> None:
        """Initialize."""
        self._hass = hass
        self._priority = priority
        self._attr_name = f"Notification Count {priority.capitalize()}"
        self._attr_unique_id = f"ha_notification_center_count_{priority}"
        self._attr_icon = (
            "mdi:alert-circle" if priority == PRIORITY_CRITICAL else "mdi:alert"
        )

    @property
    def native_value(self) -> int:
        """Return count of notifications at this priority."""
        active = self._hass.data.get(DOMAIN, {}).get("active_notifications", {})
        return sum(
            1
            for n in active.values()
            if n.get(ATTR_PRIORITY) == self._priority
        )
