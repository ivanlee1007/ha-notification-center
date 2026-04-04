"""UNiNUS Notification Center - HA custom integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_STATE_CHANGED, Platform
from homeassistant.core import (
    CoreState,
    Event,
    EventStateChangedData,
    HomeAssistant,
    ServiceCall,
    State,
)
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ACKNOWLEDGED,
    ATTR_ACKNOWLEDGED_AT,
    ATTR_DESCRIPTION,
    ATTR_EXPIRES_AT,
    ATTR_ICON,
    ATTR_NAME,
    ATTR_PRIORITY,
    ATTR_SOURCE_ID,
    ATTR_TAP_ACTION,
    ATTR_TAP_ACTION_ENTITY,
    ATTR_TAP_ACTION_SERVICE,
    ATTR_TAP_ACTION_SERVICE_DATA,
    ATTR_TAP_ACTION_SERVICE_DOMAIN,
    ATTR_TIMESTAMP,
    DOMAIN,
    PRIORITY_CRITICAL,
    PRIORITY_INFO,
    PRIORITY_WARNING,
    SERVICE_ACKNOWLEDGE,
    SERVICE_CLEAR_NOTIFICATION,
    SERVICE_PUSH_NOTIFICATION,
    SERVICE_REGISTER_SOURCE,
    SERVICE_SNOOZE,
    SERVICE_TOGGLE_DROPDOWN,
    SERVICE_UNSNOOZE,
)
from .storage import NotificationStorage

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]
SCAN_INTERVAL = timedelta(seconds=5)


def _build_notification_payload(
    source_id: str,
    name: str,
    *,
    icon: str = "mdi:bell",
    priority: str = PRIORITY_INFO,
    description: str = "",
    tap_action: str = "more-info",
    tap_action_entity: str | None = None,
    tap_action_navigation_path: str = "",
    tap_action_url_path: str = "",
    tap_action_service_domain: str = "",
    tap_action_service: str = "",
    tap_action_service_data: dict | None = None,
    timestamp: str | None = None,
    acknowledged: bool = False,
    acknowledged_at: str | None = None,
    expires_at: str | None = None,
) -> dict[str, Any]:
    """Build a normalized notification payload."""
    return {
        ATTR_SOURCE_ID: source_id,
        ATTR_NAME: name,
        ATTR_ICON: icon or "mdi:bell",
        ATTR_PRIORITY: priority if priority in (PRIORITY_INFO, PRIORITY_WARNING, PRIORITY_CRITICAL) else PRIORITY_INFO,
        ATTR_DESCRIPTION: description or "",
        ATTR_TAP_ACTION: tap_action,
        ATTR_TAP_ACTION_ENTITY: tap_action_entity,
        "tap_action_navigation_path": tap_action_navigation_path,
        "tap_action_url_path": tap_action_url_path,
        ATTR_TAP_ACTION_SERVICE_DOMAIN: tap_action_service_domain,
        ATTR_TAP_ACTION_SERVICE: tap_action_service,
        ATTR_TAP_ACTION_SERVICE_DATA: tap_action_service_data or {},
        ATTR_TIMESTAMP: timestamp or datetime.now().isoformat(),
        ATTR_ACKNOWLEDGED: bool(acknowledged),
        ATTR_ACKNOWLEDGED_AT: acknowledged_at,
        ATTR_EXPIRES_AT: expires_at,
    }


def _push_entity_updates(hass: HomeAssistant) -> None:
    """Push updated state to registered entities."""
    for sensor in hass.data[DOMAIN].get("binary_sensors", []):
        try:
            sensor.async_write_ha_state()
        except Exception as err:
            _LOGGER.debug("Failed to update binary sensor state: %s", err)

    for sensor in hass.data[DOMAIN].get("sensors", []):
        try:
            sensor.async_write_ha_state()
        except Exception as err:
            _LOGGER.debug("Failed to update sensor state: %s", err)


async def _rebuild_active_notifications(hass: HomeAssistant) -> None:
    """Rebuild merged active notifications from all sources."""
    domain_data = hass.data[DOMAIN]
    entity_notifications = domain_data.get("entity_notifications", {})
    manual_notifications = domain_data.get("manual_notifications", {})

    # Add type flag to distinguish sources
    entities = {nid: {**n, "type": "entity"} for nid, n in entity_notifications.items()}
    manuals = {nid: {**n, "type": "manual"} for nid, n in manual_notifications.items()}

    domain_data["active_notifications"] = {**entities, **manuals}
    _push_entity_updates(hass)


async def _deliver_notification(
    hass: HomeAssistant,
    *,
    name: str,
    description: str,
    priority: str,
    tap_entity: str | None,
) -> None:
    """Deliver notification using configured notify/email services."""
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
                        "push": {
                            "interruption-level": "critical" if priority == PRIORITY_CRITICAL else "active"
                        },
                        "entity_id": tap_entity,
                    },
                },
                blocking=False,
            )
        except Exception as err:
            _LOGGER.warning("Failed to send notification: %s", err)

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Notification Center component."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    storage = NotificationStorage(hass)
    await storage.async_load()
    domain_data["storage"] = storage
    domain_data["sources"] = {}
    domain_data["entity_notifications"] = {}
    domain_data["manual_notifications"] = await storage.async_get_manual_notifications()
    domain_data["active_notifications"] = {}
    domain_data["notify_service"] = "notify"
    domain_data["email_service"] = None
    domain_data["critical_repeat_interval"] = 10
    domain_data["battery_threshold"] = 20
    domain_data["dropdown_open"] = False
    await _rebuild_active_notifications(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Notification Center from a config entry."""
    options = entry.options
    hass.data[DOMAIN]["notify_service"] = options.get(
        "notify_service", entry.data.get("notify_service", "notify")
    )
    hass.data[DOMAIN]["email_service"] = options.get(
        "email_service", entry.data.get("email_service")
    )
    hass.data[DOMAIN]["critical_repeat_interval"] = options.get(
        "critical_repeat_interval", entry.data.get("critical_repeat_interval", 10)
    )
    hass.data[DOMAIN]["battery_threshold"] = options.get(
        "battery_threshold", entry.data.get("battery_threshold", 20)
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_services(hass)
    _async_setup_automations(hass)
    await _rebuild_active_notifications(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Set up services."""
    if hass.data[DOMAIN].get("services_registered"):
        return

    async def handle_register_source(call: ServiceCall) -> None:
        """Register a notification source."""
        data = dict(call.data)
        name = data.get(ATTR_NAME)
        if not name:
            _LOGGER.error("register_source requires 'name'")
            return

        source_id = str(data.get(ATTR_SOURCE_ID) or name).lower().replace(" ", "_")
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

    async def handle_push_notification(call: ServiceCall) -> None:
        """Push a manual notification directly into the feed."""
        data = dict(call.data)
        source_id = str(data.get(ATTR_SOURCE_ID) or "").strip()
        name = str(data.get(ATTR_NAME) or "").strip()
        if not source_id or not name:
            _LOGGER.error("push_notification requires 'source_id' and 'name'")
            return

        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        if await storage.async_is_snoozed(source_id):
            _LOGGER.debug("Ignoring pushed notification %s because it is snoozed", source_id)
            return

        auto_clear_seconds = data.get("auto_clear_seconds")
        expires_at = None
        if auto_clear_seconds not in (None, ""):
            try:
                auto_clear_seconds = max(1, int(auto_clear_seconds))
                expires_at = (datetime.now() + timedelta(seconds=auto_clear_seconds)).isoformat()
            except (TypeError, ValueError):
                _LOGGER.warning("Invalid auto_clear_seconds for %s: %r", source_id, auto_clear_seconds)

        payload = _build_notification_payload(
            source_id,
            name,
            icon=str(data.get(ATTR_ICON) or "mdi:bell"),
            priority=str(data.get(ATTR_PRIORITY) or PRIORITY_INFO),
            description=str(data.get(ATTR_DESCRIPTION) or ""),
            tap_action=str(data.get(ATTR_TAP_ACTION) or "more-info"),
            tap_action_entity=data.get(ATTR_TAP_ACTION_ENTITY),
            tap_action_navigation_path=str(data.get("tap_action_navigation_path") or ""),
            tap_action_url_path=str(data.get("tap_action_url_path") or ""),
            tap_action_service_domain=str(data.get(ATTR_TAP_ACTION_SERVICE_DOMAIN) or ""),
            tap_action_service=str(data.get(ATTR_TAP_ACTION_SERVICE) or ""),
            tap_action_service_data=data.get(ATTR_TAP_ACTION_SERVICE_DATA),
            timestamp=datetime.now().isoformat(),
            acknowledged=bool(data.get(ATTR_ACKNOWLEDGED, False)),
            acknowledged_at=data.get(ATTR_ACKNOWLEDGED_AT),
            expires_at=expires_at,
        )
        hass.data[DOMAIN]["manual_notifications"][source_id] = payload
        await storage.async_set_manual_notification(source_id, payload)
        await _rebuild_active_notifications(hass)

    async def handle_clear_notification(call: ServiceCall) -> None:
        """Clear a manual notification from the feed."""
        source_id = str(call.data.get(ATTR_SOURCE_ID) or "").strip()
        if not source_id:
            _LOGGER.error("clear_notification requires 'source_id'")
            return
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        hass.data[DOMAIN].get("manual_notifications", {}).pop(source_id, None)
        await storage.async_remove_manual_notification(source_id)
        await storage.async_clear_acknowledge(source_id)
        await storage.async_clear_last_repeat(source_id)
        await _rebuild_active_notifications(hass)

    async def handle_snooze(call: ServiceCall) -> None:
        """Snooze a notification source."""
        source_id = call.data.get("source_id")
        duration = call.data.get("duration_hours", 1)
        if not source_id:
            return
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        await storage.async_set_snooze(source_id, duration)
        hass.data[DOMAIN].get("manual_notifications", {}).pop(source_id, None)
        await storage.async_remove_manual_notification(source_id)
        await _rebuild_active_notifications(hass)
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
        source_id = str(source_id)
        storage: NotificationStorage = hass.data[DOMAIN]["storage"]
        await storage.async_acknowledge(source_id)
        acknowledged_at = datetime.now().isoformat()
        for bucket_name in ("entity_notifications", "manual_notifications"):
            bucket = hass.data[DOMAIN].get(bucket_name, {})
            if source_id in bucket:
                bucket[source_id][ATTR_ACKNOWLEDGED] = True
                bucket[source_id][ATTR_ACKNOWLEDGED_AT] = acknowledged_at
        manual = hass.data[DOMAIN].get("manual_notifications", {}).get(source_id)
        if manual:
            await storage.async_set_manual_notification(source_id, manual)
        await _rebuild_active_notifications(hass)

    async def handle_toggle_dropdown(call: ServiceCall) -> None:
        """Toggle notification dropdown open/close state."""
        hass.data[DOMAIN]["dropdown_open"] = not hass.data[DOMAIN].get("dropdown_open", False)
        _push_entity_updates(hass)

    hass.services.async_register(DOMAIN, SERVICE_REGISTER_SOURCE, handle_register_source)
    hass.services.async_register(DOMAIN, SERVICE_PUSH_NOTIFICATION, handle_push_notification)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_NOTIFICATION, handle_clear_notification)
    hass.services.async_register(DOMAIN, SERVICE_SNOOZE, handle_snooze)
    hass.services.async_register(DOMAIN, SERVICE_UNSNOOZE, handle_unsnooze)
    hass.services.async_register(DOMAIN, SERVICE_ACKNOWLEDGE, handle_acknowledge)
    hass.services.async_register(DOMAIN, SERVICE_TOGGLE_DROPDOWN, handle_toggle_dropdown)
    hass.data[DOMAIN]["services_registered"] = True


def _async_setup_automations(hass: HomeAssistant) -> None:
    """Set up automation-like state tracking and delivery logic."""
    if hass.data[DOMAIN].get("automation_tracking_started"):
        return

    storage: NotificationStorage = hass.data[DOMAIN]["storage"]

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
        if source_id in ("notification_any_active", "notification_any_critical", "notification_any_warning"):
            return

        entity_notifications: dict[str, dict[str, Any]] = hass.data[DOMAIN].setdefault("entity_notifications", {})
        is_on = new_state.state == "on"
        was_on = old_state.state == "on" if old_state else False

        if await storage.async_is_snoozed(source_id):
            if source_id in entity_notifications:
                del entity_notifications[source_id]
                await _rebuild_active_notifications(hass)
            return

        if is_on and not was_on:
            priority = str(new_state.attributes.get("priority", PRIORITY_INFO))
            name = str(new_state.attributes.get("friendly_name", source_id))
            icon = str(new_state.attributes.get("icon", "mdi:bell"))
            description = str(new_state.attributes.get("description", ""))
            tap_act = str(new_state.attributes.get("tap_action", "more-info"))
            tap_entity = new_state.attributes.get("tap_action_entity", entity_id)
            tap_nav_path = str(new_state.attributes.get("tap_action_navigation_path", ""))
            tap_url_path = str(new_state.attributes.get("tap_action_url_path", ""))
            acknowledged = await storage.is_acknowledged(source_id)
            acknowledged_at = await storage.async_get_acknowledged_at(source_id)

            entity_notifications[source_id] = _build_notification_payload(
                source_id,
                name,
                icon=icon,
                priority=priority,
                description=description,
                tap_action=tap_act,
                tap_action_entity=tap_entity,
                tap_action_navigation_path=tap_nav_path,
                tap_action_url_path=tap_url_path,
                tap_action_service_domain=str(new_state.attributes.get("tap_action_service_domain", "") or ""),
                tap_action_service=str(new_state.attributes.get("tap_action_service", "") or ""),
                tap_action_service_data=new_state.attributes.get("tap_action_service_data"),
                timestamp=new_state.last_changed.isoformat(),
                acknowledged=acknowledged,
                acknowledged_at=acknowledged_at,
            )
            await _deliver_notification(
                hass,
                name=name,
                description=description,
                priority=priority,
                tap_entity=tap_entity,
            )

        elif not is_on and was_on:
            entity_notifications.pop(source_id, None)
            await storage.async_clear_last_repeat(source_id)
            await storage.async_clear_acknowledge(source_id)

        await _rebuild_active_notifications(hass)

    async def _setup_tracking(event: Event | None) -> None:
        hass.bus.async_listen(EVENT_STATE_CHANGED, _handle_state_change)
        _LOGGER.info("Notification state tracking started")

    if hass.state == CoreState.running:
        hass.async_create_task(_setup_tracking(None))
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _setup_tracking)

    async def _check_critical_repeat(now) -> None:
        """Repeat critical notifications and clear expired manual notifications."""
        repeat_interval = hass.data[DOMAIN].get("critical_repeat_interval", 10)
        refreshed_manual = await storage.async_get_manual_notifications()
        if refreshed_manual != hass.data[DOMAIN].get("manual_notifications", {}):
            hass.data[DOMAIN]["manual_notifications"] = refreshed_manual
            await _rebuild_active_notifications(hass)

        active_notifications = hass.data[DOMAIN].get("active_notifications", {})
        for nid, notif in active_notifications.items():
            if notif.get(ATTR_PRIORITY) == PRIORITY_CRITICAL and not notif.get(ATTR_ACKNOWLEDGED):
                if await storage.should_repeat(nid, repeat_interval):
                    await _deliver_notification(
                        hass,
                        name=notif.get(ATTR_NAME, nid),
                        description=notif.get(ATTR_DESCRIPTION, "") or f"{notif.get(ATTR_NAME, nid)} is still active",
                        priority=PRIORITY_CRITICAL,
                        tap_entity=notif.get(ATTR_TAP_ACTION_ENTITY),
                    )
                    await storage.async_set_last_repeat(nid)

    async_track_time_interval(hass, _check_critical_repeat, timedelta(minutes=1))
    hass.data[DOMAIN]["automation_tracking_started"] = True
