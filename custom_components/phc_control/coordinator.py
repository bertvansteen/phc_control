"""Update coordinator for PHC."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL, DeviceResponseEntry
from .phcgateway import PHCGateway

_LOGGER = logging.getLogger(__name__)


class PHCUpdateCoordinator(DataUpdateCoordinator[DeviceResponseEntry]):
    """Gather data for the energy device."""

    gateway: PHCGateway
    api_disabled: bool = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
    ) -> None:
        """Initialize Update Coordinator."""

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.entry = entry
        self.gateway = PHCGateway(host)

    async def _async_update_data(self) -> DeviceResponseEntry:
        """Fetch all device and sensor data from api."""
        output_modules = await self.hass.async_add_executor_job(
            self.gateway.get_output_modules
        )
        output_data = {}
        for output_module in output_modules:
            output_data[output_module.address] = await self.hass.async_add_executor_job(
                self.gateway.get_output_status, output_module.address
            )

        dimmer_modules = await self.hass.async_add_executor_job(
            self.gateway.get_dimmer_modules
        )
        dimmer_data = {}
        for dimmer_module in dimmer_modules:
            dimmer_data[dimmer_module.address] = await self.hass.async_add_executor_job(
                self.gateway.get_dimmer_status, dimmer_module.address
            )

        data = DeviceResponseEntry(output=output_data, dimmer=dimmer_data)
        # Update all properties
        # try:
        # data = DeviceResponseEntry(
        #     device=await self.api.device(),
        #     data=await self.api.data(),
        #     features=await self.api.features(),
        #     state=await self.api.state(),
        # )

        # if data.features.has_system:
        #     data.system = await self.api.system()

        # except Error as ex:
        #     raise UpdateFailed(ex) from ex

        # except DisabledError as ex:
        #     if not self.api_disabled:
        #         self.api_disabled = True

        #         # Do not reload when performing first refresh
        #         if self.data is not None:
        #             await self.hass.config_entries.async_reload(self.entry.entry_id)

        #     raise UpdateFailed(ex) from ex

        self.api_disabled = False

        return data
