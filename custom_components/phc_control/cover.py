"""Platform for light integration."""
from __future__ import annotations
from typing import Any

import logging
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

import homeassistant.helpers.config_validation as cv

from homeassistant.components.cover import (
    ATTR_POSITION,
    PLATFORM_SCHEMA,
    CoverEntity,
    CoverEntityFeature,
)

from homeassistant.const import (
    CONF_HOST,
    CONF_ADDRESS,
    CONF_TYPE,
)

from .const import DOMAIN
from .coordinator import PHCUpdateCoordinator
from .entity import PHCEntity
from .phcgateway import PHCGateway

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_ADDRESS): cv.positive_float,
        vol.Optional(CONF_TYPE): cv.string,
    }
)


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
    coordinator: PHCUpdateCoordinator = hass.data[DOMAIN][
        str(entry.entry_id) + "_coordinator"
    ]
    gateway: PHCGateway = hass.data[DOMAIN][str(entry.entry_id) + "_gateway"]

    output_modules = await hass.async_add_executor_job(gateway.get_shutter_modules)
    for module in output_modules:
        for key in module.channels:
            add_entities(
                [
                    PhcCoverEntity(
                        "Output",
                        module.address,
                        key,
                        module.channels.get(key).name,
                        module.channels.get(key).runtime,
                        gateway,
                        coordinator,
                    )
                ],
                False,
            )


class PhcCoverEntity(CoverEntity, PHCEntity):
    """Representation of a Sensor."""

    def __init__(
        self,
        type: str,
        address: int,
        channel: int,
        channel_name: str,
        runtime: int,
        phc_gateway: PHCGateway,
        coordinator: PHCUpdateCoordinator,
    ) -> None:
        super().__init__(type, address, coordinator)

        self._address = address
        self._channel = channel
        self._phc_gateway = phc_gateway
        self._name = channel_name
        self._attr_is_closed = None
        self._attr_is_closing = None
        self._attr_is_opening = None
        self._runtime = runtime

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name or self.unique_id

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return "" + str(self._address) + " " + str(self._channel)

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of the roller blind.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return 50

    @property
    def supported_features(self) -> CoverEntityFeature:
        """Flag supported features."""
        supported_features = CoverEntityFeature(0)
        supported_features |= (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

        return supported_features

    def close_cover(self, **kwargs: Any) -> None:
        """Close the roller."""
        self._phc_gateway.close_shutter(self._address, self._channel, self._runtime)

    def open_cover(self, **kwargs: Any) -> None:
        """Open the roller."""
        self._phc_gateway.open_shutter(self._address, self._channel, self._runtime)

    def stop_cover(self, **kwargs: Any) -> None:
        """Stop the roller."""
        self._phc_gateway.stop_shutter(self._address, self._channel)
