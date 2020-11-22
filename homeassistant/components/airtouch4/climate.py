"""AirTouch 4 component to control of AirTouch 4 Climate Devices."""

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE
AT_TO_HA_STATE = {
    "Heat": HVAC_MODE_HEAT,
    "Cool": HVAC_MODE_COOL,
    "Auto": HVAC_MODE_HEAT_COOL,
    "Dry": HVAC_MODE_DRY,
    "Fan": HVAC_MODE_FAN_ONLY,
}

HA_STATE_TO_AT = {value: key for key, value in AT_TO_HA_STATE.items()}

AT_TO_HA_FAN_SPEED = {
    "Quiet": FAN_DIFFUSE,
    "Low": FAN_LOW,
    "Medium": FAN_MEDIUM,
    "High": FAN_HIGH,
    "Powerful": FAN_FOCUS,
    "Auto": FAN_AUTO,
}

HA_FAN_SPEED_TO_AT = {value: key for key, value in AT_TO_HA_FAN_SPEED.items()}

_LOGGER = logging.getLogger(__name__)


def _build_entity(coordinator, groupNumber, info, airtouch):
    _LOGGER.debug("Found device %s", groupNumber)
    return AirtouchGroup(coordinator, groupNumber, info, airtouch)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Set up the Airtouch 4."""
    info = hass.data["airtouch4"][config_entry.entry_id]["info"]
    coordinator = hass.data["airtouch4"][config_entry.entry_id]["coordinator"]

    all_devices = [
        _build_entity(coordinator, group["GroupNumber"], info, coordinator._airtouch)
        for group in info["groups"]
    ]

    async_add_devices(all_devices)


class AirtouchGroup(ClimateEntity, CoordinatorEntity):
    """Representation of an AirTouch 4 group."""

    def __init__(self, coordinator, group_number, info, airtouch):
        """Initialize the climate device."""
        super().__init__(coordinator)
        self._group_number = group_number
        self._airtouch = airtouch
        self._info = info
        self._unit = airtouch.GetGroupByGroupNumber(self._group_number)

    @callback
    def _handle_coordinator_update(self):
        self._unit = self._airtouch.GetGroupByGroupNumber(self._group_number)
        return super()._handle_coordinator_update()

    @property
    def device_info(self):
        """Return device info for this device."""
        return {
            "identifiers": {("airtouch4", self._group_number)},
            "name": self.name,
            "manufacturer": "Airtouch",
            "model": "Airtouch 4",
        }

    @property
    def unique_id(self):
        """Return unique ID for this device."""
        return self._group_number

    @property
    def min_temp(self):
        """Return Minimum Temperature for AC of this group."""
        return self._airtouch.acs[self._unit.BelongsToAc].MinSetpoint

    @property
    def max_temp(self):
        """Return Max Temperature for AC of this group."""
        return self._airtouch.acs[self._unit.BelongsToAc].MaxSetpoint

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._unit.GroupName

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._unit.Temperature

    @property
    def target_temperature(self):
        """Return the temperature we are trying to reach."""
        return self._unit.TargetSetpoint

    @property
    def hvac_mode(self):
        """Return hvac target hvac state."""
        # mode = self._unit.mode
        is_on = self._unit.PowerState == "On"
        if not is_on:
            return HVAC_MODE_OFF

        return AT_TO_HA_STATE[self._airtouch.acs[self._unit.BelongsToAc].AcMode]

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        airtouchModes = self._airtouch.GetSupportedCoolingModesByGroup(
            self._group_number
        )
        modes = [AT_TO_HA_STATE[mode] for mode in airtouchModes]
        modes.extend([HVAC_MODE_OFF])
        return modes

    @property
    def fan_mode(self):
        """Return fan mode of the AC this group belongs to."""
        return AT_TO_HA_FAN_SPEED[self._airtouch.acs[self._unit.BelongsToAc].AcFanSpeed]

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        airtouchFanSpeeds = self._airtouch.GetSupportedFanSpeedsByGroup(
            self._group_number
        )
        return [AT_TO_HA_FAN_SPEED[speed] for speed in airtouchFanSpeeds]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            _LOGGER.debug("Setting temp of %s to %s", self._group_number, str(temp))
            self._unit = self._airtouch.SetGroupToTemperature(
                self._group_number, int(temp)
            )
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        """Set new fan mode."""
        _LOGGER.debug("Setting fan mode of %s to %s", self._group_number, fan_mode)
        self._unit = self._airtouch.SetFanSpeedByGroup(
            self._group_number, HA_FAN_SPEED_TO_AT[fan_mode]
        )
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new operation mode."""
        if hvac_mode == HVAC_MODE_OFF:
            return await self.async_turn_off()
        if self.hvac_mode == HVAC_MODE_OFF:
            await self.async_turn_on()
        self._unit = self._airtouch.SetCoolingModeByGroup(
            self._group_number, HA_STATE_TO_AT[hvac_mode]
        )
        _LOGGER.debug(
            "Setting operation mode of %s to %s", self._group_number, hvac_mode
        )
        self.async_write_ha_state()

    async def async_turn_on(self):
        """Turn on."""
        _LOGGER.debug("Turning %s on", self.unique_id)
        self._airtouch.TurnGroupOn(self._group_number)

        # in case ac is not on. Airtouch turns itself off if no groups are turned on (even if groups turned back on)
        self._airtouch.TurnAcOn(
            self._airtouch.GetGroupByGroupNumber(self._group_number).BelongsToAc
        )
        self.async_write_ha_state()

    async def async_turn_off(self):
        """Turn off."""
        _LOGGER.debug("Turning %s off", self.unique_id)
        self._airtouch.TurnGroupOff(self._group_number)
        self.async_write_ha_state()
