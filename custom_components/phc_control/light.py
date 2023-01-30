"""Platform for light integration."""
from __future__ import annotations
from typing import Any

import requests
import logging
import voluptuous as vol
from config.custom_components.phc_control.coordinator import PHCUpdateCoordinator
from config.custom_components.phc_control.entity import PHCEntity
from config.custom_components.phc_control.phcgateway import PHCGateway
from homeassistant.core import HomeAssistant

import homeassistant.helpers.config_validation as cv
import xml.etree.ElementTree as ET

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_TRANSITION,
    PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_ADDRESS,
    CONF_TYPE,
)

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_ADDRESS): cv.positive_float,
        vol.Optional(CONF_TYPE): cv.string,
    }
)

from .const import DOMAIN


# def setup_platform(
#     hass: HomeAssistant,
#     config: ConfigType,
#     add_entities: AddEntitiesCallback,
#     discovery_info: DiscoveryInfoType | None = None,
# ) -> None:
#     """Set up the PHC Lights platform."""
#     host = config[CONF_HOST]
#     address = config[CONF_ADDRESS]
#     phc_device = PhcOutputDevice(host)

#     for channel in range(0, 7):
#         add_entities([PhcOutputLightSensor(address, channel, phc_device)], True)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigType, add_entities: AddEntitiesCallback
) -> None:
    """Set up the PHC Lights platform."""
    host = entry.data[CONF_HOST]

    coordinator: PHCUpdateCoordinator = hass.data[DOMAIN][
        str(entry.entry_id) + "_coordinator"
    ]
    gateway: PHCGateway = hass.data[DOMAIN][str(entry.entry_id) + "_gateway"]

    output_modules = await hass.async_add_executor_job(gateway.get_output_modules)
    for module in output_modules:
        for key in module.channels:
            add_entities(
                [
                    PhcOutputLightSensor(
                        "Output",
                        module.address,
                        key,
                        module.channels.get(key),
                        gateway,
                        coordinator,
                    )
                ],
                False,
            )

    dimmer_modules = await hass.async_add_executor_job(gateway.get_dimmer_modules)
    for module in dimmer_modules:
        for key in module.channels:
            add_entities(
                [
                    PhcDimmerLightSensor(
                        "Dimmer",
                        module.address,
                        key,
                        module.channels.get(key),
                        gateway,
                        coordinator,
                    )
                ],
                False,
            )


class PhcOutputDevice:
    """PCH output module gateway."""

    def __init__(self, host) -> None:
        self._host = host


class PhcOutputLightSensor(LightEntity, PHCEntity):
    """Representation of a Sensor."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(
        self,
        type: str,
        address: int,
        channel: int,
        channel_name: str,
        phc_gateway: PHCGateway,
        coordinator: PHCUpdateCoordinator,
    ) -> None:
        super().__init__(type, address, coordinator)

        self._address = address
        self._channel = channel
        self._phc_gateway = phc_gateway
        self._name = channel_name

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name or self.unique_id

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return "" + str(self._address) + " " + str(self._channel)

    def turn_on(self, **kwargs):
        """Turn light on."""
        self._phc_gateway.turn_output_on(self._address, self._channel)
        self.coordinator.data.output[self._address].states[self._channel] = True
        self.coordinator.async_update_listeners()

    def turn_off(self, **kwargs):
        """Turn light off."""
        self._phc_gateway.turn_output_off(self._address, self._channel)
        self.coordinator.data.output[self._address].states[self._channel] = False
        self.coordinator.async_update_listeners()

    @property
    def is_on(self):
        """Return whether this light is on or off."""
        if self.coordinator.data is None:
            return None
        moduledata = self.coordinator.data.output.get(self._address)

        if moduledata is None:
            return None
        return moduledata.states[self._channel]


class PhcDimmerLightSensor(LightEntity, PHCEntity):
    """Representation of a Sensor."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(
        self,
        type: str,
        address: int,
        channel: int,
        channel_name: str,
        phc_gateway: PHCGateway,
        coordinator: PHCUpdateCoordinator,
    ) -> None:
        super().__init__(type, address, coordinator)

        self._address = address
        self._channel = channel
        self._phc_gateway = phc_gateway
        self._name = channel_name
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name or self.unique_id

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return "" + str(self._address) + " " + str(self._channel)

    def turn_on(self, **kwargs):
        """Turn light on."""
        attribs: dict[str, Any] = {}

        if ATTR_BRIGHTNESS in kwargs:
            brightness = int(kwargs[ATTR_BRIGHTNESS])
            attribs["brightness"] = brightness

            self._phc_gateway.turn_dimmer_set(self._address, self._channel, brightness)
            self.coordinator.data.dimmer[self._address].states[
                self._channel
            ] = brightness
            self.coordinator.async_update_listeners()
        else:
            self._phc_gateway.turn_dimmer_on(self._address, self._channel)
            self.coordinator.data.dimmer[self._address].states[self._channel] = 128
            self.coordinator.async_update_listeners()

    def turn_off(self, **kwargs):
        """Turn light off."""
        # self._phc_gateway.turn_output_off(self._address, self._channel)
        self._phc_gateway.turn_dimmer_off(self._address, self._channel)
        self.coordinator.data.dimmer[self._address].states[self._channel] = 0
        self.coordinator.async_update_listeners()

    @property
    def is_on(self):
        """Return whether this light is on or off."""
        if self.coordinator.data is None:
            return None
        moduledata = self.coordinator.data.dimmer.get(self._address)

        if moduledata is None:
            return None

        # print(
        #     f"value for DIM{str(self._address)}.{str(self._channel)}: {moduledata.states[self._channel]}"
        # )
        return moduledata.states[self._channel] > 0

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if self.coordinator.data is None:
            return None
        moduledata = self.coordinator.data.dimmer.get(self._address)

        if moduledata is None:
            return None

        # print(
        #     f"value for DIM{str(self._address)}.{str(self._channel)}: {moduledata.states[self._channel]}"
        # )
        return moduledata.states[self._channel]

    async def async_update(self) -> None:
        """Update brightness."""
        # current_intensity = (
        #     await self.device.api.vapix.light_control.get_current_intensity(
        #         self.light_id
        #     )
        # )
        # self.current_intensity = current_intensity["data"]["intensity"]
        print(f"update called for DIM{str(self._address)}.{str(self._channel)}")

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return LightEntityFeature(0)
