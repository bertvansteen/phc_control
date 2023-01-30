"""Base entity for the HomeWizard integration."""
from __future__ import annotations

from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PHCUpdateCoordinator


class PHCEntity(CoordinatorEntity[PHCUpdateCoordinator]):
    """Defines a HomeWizard Capacity entity."""

    _attr_has_entity_name = True

    def __init__(self, type, address, coordinator: PHCUpdateCoordinator) -> None:
        """Initialize the HomeWizard Capacity entity."""
        self._type = type
        self._address = address

        super().__init__(coordinator=coordinator)
        self._attr_device_info = DeviceInfo(
            name="PHC " + type + " (" + str(address) + ")",
            manufacturer="Peha",
            sw_version="1",
            model="PHC " + type,
        )
