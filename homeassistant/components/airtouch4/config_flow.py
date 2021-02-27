"""Config flow for AirTouch4."""
from airtouch4pyapi import AirTouch
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


def _createAirtouchObject(host):
    return AirTouch(host)


async def _validate_connection(hass: core.HomeAssistant, host):
    airtouch = await hass.async_add_executor_job(_createAirtouchObject)

    if hasattr(airtouch, "error"):
        return airtouch.error
    return bool(airtouch.GetGroups())


class AirtouchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Airtouch config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @core.callback
    def _async_get_entry(self, data):

        return self.async_create_entry(
            title=data[CONF_HOST],
            data={
                CONF_HOST: data[CONF_HOST],
            },
        )

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        errors = {}

        host = user_input[CONF_HOST]

        await self.async_set_unique_id(user_input[CONF_HOST])
        self._abort_if_unique_id_configured()

        try:
            result = await _validate_connection(self.hass, host)
            if not result:
                errors["base"] = "no_units"
            elif isinstance(result, OSError):
                errors["base"] = "cannot_connect"
        except Exception:
            errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        return self._async_get_entry(user_input)
