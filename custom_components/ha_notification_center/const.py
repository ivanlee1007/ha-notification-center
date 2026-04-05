# Copyright [yyyy] [name of copyright owner]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Constants for UNiNUS Notification Center."""
from typing import Final

DOMAIN: Final = "ha_notification_center"

# Attributes
ATTR_NAME: Final = "name"
ATTR_ICON: Final = "icon"
ATTR_PRIORITY: Final = "priority"
ATTR_DESCRIPTION: Final = "description"
ATTR_TAP_ACTION: Final = "tap_action"
ATTR_TAP_ACTION_ACTION: Final = "tap_action_action"
ATTR_TAP_ACTION_ENTITY: Final = "tap_action_entity"
ATTR_TAP_ACTION_SERVICE_DOMAIN: Final = "tap_action_service_domain"
ATTR_TAP_ACTION_SERVICE: Final = "tap_action_service"
ATTR_TAP_ACTION_SERVICE_DATA: Final = "tap_action_service_data"
ATTR_TIMESTAMP: Final = "timestamp"
ATTR_EXPIRES_AT: Final = "expires_at"
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
SERVICE_TOGGLE_DROPDOWN: Final = "toggle_dropdown"
SERVICE_PUSH_NOTIFICATION: Final = "push_notification"
SERVICE_CLEAR_NOTIFICATION: Final = "clear_notification"
SERVICE_EXECUTE_TAP_ACTION: Final = "execute_tap_action"

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
