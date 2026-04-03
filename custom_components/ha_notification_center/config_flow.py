"""Config flow for UNiNUS Notification Center."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_BATTERY_THRESHOLD,
    CONF_CRITICAL_REPEAT_INTERVAL,
    CONF_EMAIL_SERVICE,
    CONF_NOTIFY_SERVICE,
    DOMAIN,
)


class NotificationCenterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Notification Center."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title="Notification Center",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NOTIFY_SERVICE, default="notify"
                    ): str,
                    vol.Optional(CONF_EMAIL_SERVICE): str,
                    vol.Optional(
                        CONF_CRITICAL_REPEAT_INTERVAL, default=10
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=120)),
                    vol.Optional(
                        CONF_BATTERY_THRESHOLD, default=20
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NotificationCenterOptionsFlow()


class NotificationCenterOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def _current_value(self, key: str, default=None):
        """Return effective current value from options, then data, then default."""
        if key in self.config_entry.options:
            return self.config_entry.options.get(key)
        return self.config_entry.data.get(key, default)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NOTIFY_SERVICE,
                        default=self._current_value(CONF_NOTIFY_SERVICE, "notify"),
                    ): str,
                    vol.Optional(
                        CONF_EMAIL_SERVICE,
                        default=self._current_value(CONF_EMAIL_SERVICE, ""),
                    ): str,
                    vol.Optional(
                        CONF_CRITICAL_REPEAT_INTERVAL,
                        default=self._current_value(CONF_CRITICAL_REPEAT_INTERVAL, 10),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=120)),
                    vol.Optional(
                        CONF_BATTERY_THRESHOLD,
                        default=self._current_value(CONF_BATTERY_THRESHOLD, 20),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
                }
            ),
        )
