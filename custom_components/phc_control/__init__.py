"""Platform for switch integration."""
from __future__ import annotations
from typing import Any

from homeassistant.const import *
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.core import HomeAssistant

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import *
from .coordinator import PHCUpdateCoordinator as Coordinator
from .phcgateway import PHCGateway

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]):
    """Set up the Miele platform. called with config entry"""

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homewizard Capacity from a config entry."""
    gateway = PHCGateway(entry.data[CONF_HOST])
    coordinator = Coordinator(hass, entry, gateway)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][str(entry.entry_id) + "_coordinator"] = coordinator
    hass.data[DOMAIN][str(entry.entry_id) + "_gateway"] = gateway

    # Abort reauth config flow if active
    for progress_flow in hass.config_entries.flow.async_progress_by_handler(DOMAIN):
        if (
            "context" in progress_flow
            and progress_flow["context"].get("source") == SOURCE_REAUTH
        ):
            hass.config_entries.flow.async_abort(progress_flow["flow_id"])

    # Finalize
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass, coordinator)
    return True


def _async_register_services(
    hass: HomeAssistant,
    coordinator: Coordinator,
) -> None:
    """Register integration-level services."""

    async def async_refresh(call: ServiceCall) -> None:
        """Service call to pause downloads in NZBGet."""
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_REFRESH, async_refresh, schema=vol.Schema({})
    )


async def _async_update_data(self):
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unload_ok
