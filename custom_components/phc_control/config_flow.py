"""Config flow for HomeWizard."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, NamedTuple

from voluptuous import Required, Schema

from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from .phcgateway import PHCGateway
from homeassistant import config_entries

import voluptuous as vol
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import CONF_HOST, CONF_IP_ADDRESS
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_PATH,
    DOMAIN,
)

import logging

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
    }
)


class PHCConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eight Sleep."""

    VERSION = 1

    async def _validate_data(self, config: dict[str, str]) -> str | None:
        """Validate input data and return any error."""
        await self.async_set_unique_id(config[CONF_HOST].lower().replace(".", "_"))
        self._abort_if_unique_id_configured()

        eight = PHCGateway(
            config[CONF_HOST],
            #            client_session=async_get_clientsession(self.hass),
        )

        # try:
        #    eight.check_host()
        # except RequestError as err:
        #     return str(err)

        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        if (err := await self._validate_data(user_input)) is not None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                errors={"base": "cannot_connect"},
                description_placeholders={"error": err},
            )

        return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

    async def async_step_import(self, import_config: dict) -> FlowResult:
        """Handle import."""
        if (err := await self._validate_data(import_config)) is not None:
            _LOGGER.error("Unable to import configuration.yaml configuration: %s", err)
            return self.async_abort(
                reason="cannot_connect", description_placeholders={"error": err}
            )

        return self.async_create_entry(
            title="PHC: " + import_config[CONF_HOST], data=import_config
        )
