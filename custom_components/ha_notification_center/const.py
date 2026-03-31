"""Constants for UNiNUS Notification Center."""
from typing import Final

DOMAIN: Final = "ha_notification_center"

# Attributes
ATTR_NAME: Final = "name"
ATTR_ICON: Final = "icon"
ATTR_PRIORITY: Final = "priority"
ATTR_DESCRIPTION: Final = "description"
ATTR_TAP_ACTION_ENTITY: Final = "tap_action_entity"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_ACKNOWLEDGED: Final = "acknowledged"
ATTR_ACKNOWLEDGED_AT: Final = "acknowledged_at"
ATTR_SOURCE_ID: Final = "source_id"

# Priority levels
PRIORITY_INFO: Final = "info"
PRIORITY_WARNING: Final = "warning"
PRIORITY_CRITICAL: Final = "critical"

# Services
SERVICE_REGISTER_SOURCE: Final = "register_source"
SERVICE_SNOOZE: Final = "snooze"
SERVICE_UNSNOOZE: Final = "unsnooze"
SERVICE_ACKNOWLEDGE: Final = "acknowledge"

# Events
EVENT_SOURCE_ACTIVATED: Final = "ha_notification_center_source_activated"
EVENT_SOURCE_RESOLVED: Final = "ha_notification_center_source_resolved"
EVENT_NOTIFY_SNOOZED: Final = "ha_notification_center_notify_snoozed"

# Config keys
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_EMAIL_SERVICE: Final = "email_service"
CONF_CRITICAL_REPEAT_INTERVAL: Final = "critical_repeat_interval"
CONF_BATTERY_THRESHOLD: Final = "battery_threshold"

# Storage
STORAGE_KEY: Final = "ha_notification_center"
STORAGE_VERSION: Final = 1
