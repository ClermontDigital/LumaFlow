"""Config flow for LumaFlow integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_LIGHTS,
    CONF_GROUP_NAME,
    CONF_SUNSET_OFFSET,
    CONF_TRANSITION_SPEED,
    CONF_MIN_BRIGHTNESS,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_COLOR_TEMP,
    CONF_MAX_COLOR_TEMP,
    CONF_ENABLE_OVERRIDE_DETECTION,
    CONF_RESTORE_ON_STARTUP,
    DEFAULT_SUNSET_OFFSET,
    DEFAULT_TRANSITION_SPEED,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MAX_COLOR_TEMP,
    DEFAULT_ENABLE_OVERRIDE_DETECTION,
    DEFAULT_RESTORE_ON_STARTUP,
    DOMAIN,
    NAME,
)

_LOGGER = logging.getLogger(__name__)


class LumaFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LumaFlow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step - create light group."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate input
            group_name = user_input.get(CONF_GROUP_NAME, "").strip()
            lights = user_input.get(CONF_LIGHTS, [])
            
            if not group_name:
                errors["base"] = "no_group_name"
            elif not lights:
                errors["base"] = "no_lights_selected"
            else:
                # Check if group name would create duplicate entity
                entity_id = f"light.{group_name.lower().replace(' ', '_')}_lumaflow"
                if entity_id in self.hass.states.async_entity_ids("light"):
                    errors["base"] = "group_name_exists"
                else:
                    # Store data and move to timing configuration
                    self._data.update(user_input)
                    return await self.async_step_timing()

        # Get available lights
        light_entities = await self._get_light_entities()
        
        if not light_entities:
            return self.async_abort(reason="no_lights_found")

        data_schema = vol.Schema({
            vol.Required(CONF_GROUP_NAME): str,
            vol.Required(CONF_LIGHTS): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="light",
                    multiple=True,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "light_count": str(len(light_entities))
            }
        )

    async def async_step_timing(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle timing configuration step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate timing settings
            if user_input[CONF_MIN_BRIGHTNESS] >= user_input[CONF_MAX_BRIGHTNESS]:
                errors["base"] = "invalid_brightness_range"
            elif user_input[CONF_MIN_COLOR_TEMP] >= user_input[CONF_MAX_COLOR_TEMP]:
                errors["base"] = "invalid_color_temp_range"
            else:
                # Store timing settings and move to advanced options
                self._data.update(user_input)
                return await self.async_step_advanced()

        data_schema = vol.Schema({
            vol.Required(
                CONF_SUNSET_OFFSET, default=DEFAULT_SUNSET_OFFSET
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-120,
                    max=120,
                    step=5,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TRANSITION_SPEED, default=DEFAULT_TRANSITION_SPEED
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["slow", "moderate", "fast"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_MIN_BRIGHTNESS, default=DEFAULT_MIN_BRIGHTNESS
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_MAX_BRIGHTNESS, default=DEFAULT_MAX_BRIGHTNESS
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_MIN_COLOR_TEMP, default=DEFAULT_MIN_COLOR_TEMP
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=2000,
                    max=6500,
                    step=100,
                    unit_of_measurement="K",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_MAX_COLOR_TEMP, default=DEFAULT_MAX_COLOR_TEMP
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=2000,
                    max=6500,
                    step=100,
                    unit_of_measurement="K",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })

        return self.async_show_form(
            step_id="timing",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_advanced(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle advanced options step."""
        if user_input is not None:
            self._data.update(user_input)
            
            # Create the config entry with group name as title
            group_name = self._data.get(CONF_GROUP_NAME, "LumaFlow Group")
            return self.async_create_entry(
                title=f"LumaFlow - {group_name}",
                data=self._data,
            )

        data_schema = vol.Schema({
            vol.Required(
                CONF_ENABLE_OVERRIDE_DETECTION, default=DEFAULT_ENABLE_OVERRIDE_DETECTION
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_RESTORE_ON_STARTUP, default=DEFAULT_RESTORE_ON_STARTUP
            ): selector.BooleanSelector(),
        })

        return self.async_show_form(
            step_id="advanced",
            data_schema=data_schema,
        )

    async def _get_light_entities(self) -> list[str]:
        """Get available light entities."""
        entities = []
        
        for state in self.hass.states.async_all("light"):
            # Filter for colored lights or lights with color temperature support
            supported_color_modes = state.attributes.get("supported_color_modes", [])
            if any(mode in supported_color_modes for mode in ["rgb", "rgbw", "color_temp"]):
                entities.append(state.entity_id)
        
        return sorted(entities)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "LumaFlowOptionsFlow":
        """Get the options flow for this handler."""
        return LumaFlowOptionsFlow(config_entry)


class LumaFlowOptionsFlow(config_entries.OptionsFlow):
    """Handle options for LumaFlow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema({
            vol.Required(
                CONF_SUNSET_OFFSET,
                default=self.config_entry.options.get(
                    CONF_SUNSET_OFFSET,
                    self.config_entry.data.get(CONF_SUNSET_OFFSET, DEFAULT_SUNSET_OFFSET)
                )
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-120,
                    max=120,
                    step=5,
                    unit_of_measurement="minutes",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_TRANSITION_SPEED,
                default=self.config_entry.options.get(
                    CONF_TRANSITION_SPEED,
                    self.config_entry.data.get(CONF_TRANSITION_SPEED, DEFAULT_TRANSITION_SPEED)
                )
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["slow", "moderate", "fast"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_ENABLE_OVERRIDE_DETECTION,
                default=self.config_entry.options.get(
                    CONF_ENABLE_OVERRIDE_DETECTION,
                    self.config_entry.data.get(CONF_ENABLE_OVERRIDE_DETECTION, DEFAULT_ENABLE_OVERRIDE_DETECTION)
                )
            ): selector.BooleanSelector(),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        ) 