"""UNiNUS Notification Center - HA custom integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import (
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    ServiceCall,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ACKNOWLEDGED,
    ATTR_ACKNOWLEDGED_AT,
    ATTR_DESCRIPTION,
    ATTR_ICON,
    ATTR_NAME,
    ATTR_PRIORITY,
    ATTR_TAP_ACTION_ENTITY,
    ATTR_TIMESTAMP,
    DOMAIN,
    EVENT_NOTIFY_SNOOZED,
    EVENT_SOURCE_ACTIVATED,
    EVENT_SOURCE_RESOLVED,
    PRIORITY_CRITICAL,
    PRIORITY_INFO,
    PRIORITY_WARNING,
    SERVICE_ACKNOWLEDGE,
    SERVICE_REGISTER_SOURCE,
    SERVICE_SNOOZE,
    SERVICE_UNSNOOZE,
)
from .storage import NotificationStorage

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=5)
CARD_FILE = "ha-notification-center-card.js"
CARD_STATIC_URL = f"/{DOMAIN}/{CARD_FILE}"
CARD_VERSION = "1.0.2"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Notification Center component."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    storage = NotificationStorage(hass)
    await storage.async_load()
    domain_data["storage"] = storage
    domain_data["sources"] = {}
    domain_data["notify_service"] = "notify"
    domain_data["email_service"] = None
    domain_data["critical_repeat_interval"] = 10
    domain_data["battery_threshold"] = 20

    card_path = Path(__file__).parent / "www" / CARD_FILE
    if card_path.is_file() and not domain_data.get("card_static_registered"):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_STATIC_URL, str(card_path), cache_headers=False)]
            )
            domain_data["card_static_registered"] = True
            _LOGGER.info(
                "Notification Center card static path registered: %s -> %s",
                CARD_STATIC_URL,
                card_path,
            )
        except RuntimeError:
            domain_data["card_static_registered"] = True
            _LOGGER.debug(
                "Notification Center card static path already registered: %s",
                CARD_STATIC_URL,
            )
    elif not card_path.is_file():
        _LOGGER.warning("Notification Center card JS file not found: %s", card_path)

    if card_path.is_file() and not domain_data.get("card_resource_registered"):
        card_resource_url = f"{CARD_STATIC_URL}?v={CARD_VERSION}"
        try:
            frontend.add_extra_js_url(hass, card_resource_url)
            domain_data["card_resource_registered"] = True
            domain_data["card_resource_url"] = card_resource_url
            _LOGGER.info(
                "Notification Center card frontend resource registered: %s",
                card_resource_url,
            )
        except ValueError:
            domain_data["card_resource_registered"] = True
            domain_data["card_resource_url"] = card_resource_url
            _LOGGER.debug(
                "Notification Center card frontend resource already registered: %s",
                card_resource_url,
            )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notification Center from a config entry."""
    hass.data[DOMAIN]["notify_service"] = entry.data.get("notify_service", "notify")
    hass.data[DOMAIN]["email_service"] = entry.data.get("email_service")
    hass.data[DOMAIN]["critical_repeat_interval"] = entry.data.get(
        "critical_repeat_interval", 10
    )
    hass.data[DOMAIN]["battery_threshold"] = entry.data.get("battery_threshold", 20)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_services(hass)
    _async_setup_automations(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Set up services."""

    async def handle_register_source(call: ServiceCall) -> None:
        """Register a notification source."""
        data = dict(call.data)
        name = data.get(ATTR_NAME)
        if not name:
            _LOGGER.error("register_source requires 'name'")
            return

        source_id = name.lower().replace(" ", "_")
        source = {
            "id": source_id,
            ATTR_NAME: name,
            ATTR_ICON: data.get(ATTR_ICON, "mdi:bell"),
            ATTR_PRIORITY: data.get(ATTR_PRIORITY, PRIORITY_INFO),
            ATTR_DESCRIPTION: data.get(ATTR_DESCRIPTION, ""),
            ATTR_TAP_ACTION_ENTITY: data.get(ATTR_TAP_ACTION_ENTITY),
        }
        hass.data[DOMAIN]["sources"][source_id] = source
        _LOGGER.debug("Registered notification source: %s", source_id)

    async def handle_snooze(call: ServiceCall) -> None:
        """Snooze a notification source."""
        source_id = call.data.get("source_id")
        duration = call.data.get("duration_hours", 1)
        if not source_id:
            return
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        await storage.async_set_snooze(source_id, duration)
        _LOGGER.debug("Snoozed %s for %dh", source_id, duration)

    async def handle_unsnooze(call: ServiceCall) -> None:
        """Remove snooze from a notification source."""
        source_id = call.data.get("source_id")
        if not source_id:
            return
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        await storage.async_remove_snooze(source_id)

    async def handle_acknowledge(call: ServiceCall) -> None:
        """Acknowledge a notification."""
        source_id = call.data.get("source_id")
        if not source_id:
            return
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        await storage.async_acknowledge(source_id)

    hass.services.async_register(DOMAIN, SERVICE_REGISTER_SOURCE, handle_register_source)
    hass.services.async_register(DOMAIN, SERVICE_SNOOZE, handle_snooze)
    hass.services.async_register(DOMAIN, SERVICE_UNSNOOZE, handle_unsnooze)
    hass.services.async_register(DOMAIN, SERVICE_ACKNOWLEDGE, handle_acknowledge)


def _async_setup_automations(hass: HomeAssistant) -> None:
    """Set up automation-like state tracking and delivery logic."""
    storage: NotificationStorage = hass.data[DOMAIN]["storage"]
    active_notifications: dict[str, dict] = {}

    async def _handle_state_change(event: Event[EventStateChangedData]) -> None:
        """Handle binary_sensor.notification_* state changes."""
        entity_id = event.data["entity_id"]
        if not entity_id.startswith("binary_sensor.notification_"):
            return

        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")

        if new_state is None:
            return

        source_id = entity_id.replace("binary_sensor.", "")
        is_on = new_state.state == "on"
        was_on = old_state.state == "on" if old_state else False

        # Check snooze
        if await storage.async_is_snoozed(source_id):
            return

        if is_on and not was_on:
            # ACTIVATED
            priority = new_state.attributes.get("priority", PRIORITY_INFO)
            name = new_state.attributes.get("friendly_name", source_id)
            icon = new_state.attributes.get("icon", "mdi:bell")
            description = new_state.attributes.get("description", "")
            tap_entity = new_state.attributes.get("tap_action_entity", entity_id)

            active_notifications[source_id] = {
                "source_id": source_id,
                ATTR_NAME: name,
                ATTR_ICON: icon,
                ATTR_PRIORITY: priority,
                ATTR_DESCRIPTION: description,
                ATTR_TAP_ACTION_ENTITY: tap_entity,
                ATTR_TIMESTAMP: new_state.last_changed.isoformat(),
                ATTR_ACKNOWLEDGED: False,
                ATTR_ACKNOWLEDGED_AT: None,
            }

            # Deliver notification
            notify_service = hass.data[DOMAIN].get("notify_service", "notify")
            if notify_service:
                try:
                    await hass.services.async_call(
                        "notify",
                        notify_service.replace("notify.", ""),
                        {
                            "title": f"{'🚨 ' if priority == PRIORITY_CRITICAL else ''}{name}",
                            "message": description or f"{name} is active",
                            "data": {
                                "push": {"interruption-level": "critical" if priority == PRIORITY_CRITICAL else "active"},
                                "entity_id": tap_entity,
                            },
                        },
                        blocking=False,
                    )
                except Exception as err:
                    _LOGGER.warning("Failed to send notification: %s", err)

            # Email for warning/critical
            email_service = hass.data[DOMAIN].get("email_service")
            if email_service and priority in (PRIORITY_WARNING, PRIORITY_CRITICAL):
                try:
                    await hass.services.async_call(
                        "notify",
                        email_service.replace("notify.", ""),
                        {
                            "title": f"[{priority.upper()}] {name}",
                            "message": description or f"{name} is active",
                        },
                        blocking=False,
                    )
                except Exception:
                    pass

        elif not is_on and was_on:
            # RESOLVED
            if source_id in active_notifications:
                del active_notifications[source_id]

        # Store active notifications for sensor platform
        hass.data[DOMAIN]["active_notifications"] = active_notifications

    # Set up state change tracking after HA starts
    async def _setup_tracking(event: Event) -> None:
        async_track_state_change_event(
            hass, "binary_sensor.notification_*", _handle_state_change
        )
        _LOGGER.info("Notification state tracking started")

    if hass.state == CoreState.running:
        hass.async_create_task(_setup_tracking(None))
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_tracking)

    # Critical repeat delivery timer
    async def _check_critical_repeat(now) -> None:
        """Repeat critical notifications at configured interval."""
        repeat_interval = hass.data[DOMAIN].get("critical_repeat_interval", 10)
        notify_service = hass.data[DOMAIN].get("notify_service", "notify")
        if not notify_service:
            return
        for nid, notif in active_notifications.items():
            if notif[ATTR_PRIORITY] == PRIORITY_CRITICAL and not notif.get(ATTR_ACKNOWLEDGED):
                try:
                    await hass.services.async_call(
                        "notify",
                        notify_service.replace("notify.", ""),
                        {
                            "title": f"🚨 {notif[ATTR_NAME]}",
                            "message": notif[ATTR_DESCRIPTION] or f"{notif[ATTR_NAME]} is still active",
                        },
                        blocking=False,
                    )
                except Exception:
                    pass

    interval = timedelta(
        minutes=hass.data[DOMAIN].get("critical_repeat_interval", 10)
    )
    async_track_time_interval(hass, _check_critical_repeat, interval)
