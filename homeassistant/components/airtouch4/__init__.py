"""The AirTouch4 integration."""
import logging

from airtouch4pyapi import AirTouch
import voluptuous as vol

from homeassistant.components.climate import SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_HOST): str})}, extra=vol.ALLOW_EXTRA
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the AirTouch4 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up AirTouch4 from a config entry."""
    host = entry.data[CONF_HOST]
    airtouch = AirTouch(host)
    try:
        info = airtouch.GetAcs()
        if not info:
            raise ConfigEntryNotReady
    except (OSError, ConnectionRefusedError, TimeoutError) as error:
        raise ConfigEntryNotReady() from error
    coordinator = AirtouchDataUpdateCoordinator(hass, airtouch)
    await coordinator.async_refresh()
    hass.data[DOMAIN][entry.entry_id] = {
        "info": {
            "acs": [
                {"AcNumber": ac.AcNumber, "IsOn": ac.IsOn} for ac in airtouch.GetAcs()
            ],
            "groups": [
                {
                    "GroupNumber": group.GroupNumber,
                    "GroupName": group.GroupName,
                    "IsOn": group.IsOn,
                }
                for group in airtouch.GetGroups()
            ],
        },
        "coordinator": coordinator,
    }
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "climate")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class AirtouchDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Airtouch data."""

    def __init__(self, hass, airtouch):
        """Initialize global Airtouch data updater."""
        self.airtouch = airtouch

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from Airtouch."""
        try:
            self.airtouch.UpdateInfo()
            return {
                "acs": [
                    {"AcNumber": ac.AcNumber, "IsOn": ac.IsOn}
                    for ac in self.airtouch.GetAcs()
                ],
                "groups": [
                    {
                        "GroupNumber": group.GroupNumber,
                        "GroupName": group.GroupName,
                        "IsOn": group.IsOn,
                    }
                    for group in self.airtouch.GetGroups()
                ],
            }
        except (OSError, ConnectionRefusedError, TimeoutError) as error:
            raise UpdateFailed from error
