"""Configuration flows."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.typing import ConfigType
from httpx import codes

from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT, DOMAIN, OPTION_IS_FROM_FLOW
from .helper import async_verify_access, get_config_value

_LOGGER = logging.getLogger(__name__)


class SeafileConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """First time set up flow."""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SeafileOptionsFlow:
        """Get the options flow for this handler.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        :return SeafileOptionsFlow: Options Flow object
        """

        return SeafileOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: ConfigType | None = None, errors: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user.

        :param user_input: ConfigType | None: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if user_input is None:
            user_input = {}

        if errors is None:
            errors = {}

        if len(user_input) > 0:
            unique_id: str = user_input[CONF_USERNAME]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            code: codes = await async_verify_access(
                self.hass,
                user_input.get(CONF_URL),  # type: ignore
                user_input.get(CONF_USERNAME),  # type: ignore
                user_input.get(CONF_PASSWORD),  # type: ignore
                user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            )

            _LOGGER.debug("Verify access code: %s", code)

            if codes.is_success(code):
                return self.async_create_entry(
                    title=unique_id,
                    data=user_input,
                    options={OPTION_IS_FROM_FLOW: True},
                )

            if code == codes.FORBIDDEN:
                errors["base"] = "request.error"
            else:
                errors["base"] = "connection.error"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL, default=user_input.get(CONF_URL, vol.UNDEFINED)
                    ): str,
                    vol.Required(
                        CONF_USERNAME,
                        default=user_input.get(CONF_USERNAME, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=user_input.get(CONF_PASSWORD, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_SCAN_INTERVAL)),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_TIMEOUT)),
                }
            ),
            errors=errors,
        )


class SeafileOptionsFlow(config_entries.OptionsFlow):
    """Changing options flow."""

    _config_entry: config_entries.ConfigEntry

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        """

        self._config_entry = config_entry

    async def async_step_init(self, user_input: ConfigType | None = None) -> FlowResult:
        """Manage the options.

        :param user_input: ConfigType | None: User data
        """

        if user_input is None:
            user_input = {}

        errors = {}

        if len(user_input) > 0:
            full_input: dict = {
                CONF_URL: get_config_value(self._config_entry, CONF_URL),
                CONF_USERNAME: get_config_value(self._config_entry, CONF_USERNAME),
            } | user_input

            unique_id: str = full_input.get(
                CONF_USERNAME, get_config_value(self._config_entry, CONF_USERNAME)
            )

            code: codes = await async_verify_access(
                self.hass,
                full_input.get(CONF_URL),  # type: ignore
                full_input.get(CONF_USERNAME),  # type: ignore
                full_input.get(CONF_PASSWORD),  # type: ignore
                full_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            )

            _LOGGER.debug("Verify access code: %s", code)

            if codes.is_success(code):
                return self.async_create_entry(
                    title=unique_id,
                    data=full_input,
                )

            if code == codes.FORBIDDEN:
                errors["base"] = "request.error"
            else:
                errors["base"] = "connection.error"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PASSWORD,
                        default=user_input.get(CONF_PASSWORD, vol.UNDEFINED),
                    ): str,
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_SCAN_INTERVAL)),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_TIMEOUT)),
                }
            ),
            errors=errors,
        )
