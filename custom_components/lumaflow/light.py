"""Light platform for LumaFlow - creates wrapper entities with circadian behavior."""

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_LIGHTS,
    CONF_GROUP_NAME,
    ATTR_CIRCADIAN_ENABLED,
    ATTR_CURRENT_PHASE,
    ATTR_OVERRIDDEN,
    ATTR_CONTROLLED_LIGHTS,
)
from .coordinator import LumaFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LumaFlow light platform."""
    coordinator: LumaFlowCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create light entity for this group
    group_name = config_entry.data.get(CONF_GROUP_NAME, "circadian")
    controlled_lights = config_entry.data.get(CONF_LIGHTS, [])
    
    if controlled_lights:
        light_entity = LumaFlowLight(
            coordinator, 
            config_entry, 
            group_name, 
            controlled_lights
        )
        async_add_entities([light_entity])


class LumaFlowLight(CoordinatorEntity[LumaFlowCoordinator], LightEntity):
    """LumaFlow wrapper light entity with circadian behavior."""

    def __init__(
        self,
        coordinator: LumaFlowCoordinator,
        config_entry: ConfigEntry,
        group_name: str,
        controlled_lights: List[str],
    ) -> None:
        """Initialize the LumaFlow light."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._group_name = group_name
        self._controlled_lights = controlled_lights
        self._circadian_enabled = True
        self._overridden = False
        
        # Entity naming: group_name_lumaflow
        self._attr_unique_id = f"{config_entry.entry_id}_{group_name}_lumaflow"
        self._attr_name = f"{group_name.title()} LumaFlow"
        self._attr_icon = "mdi:weather-sunset"
        
        # Determine supported color modes based on controlled lights
        self._attr_supported_color_modes = self._determine_supported_color_modes()
        self._attr_color_mode = self._get_preferred_color_mode()

    def _determine_supported_color_modes(self) -> set[ColorMode]:
        """Determine supported color modes from controlled lights."""
        supported_modes = set()
        
        for light_id in self._controlled_lights:
            light_state = self.hass.states.get(light_id)
            if light_state:
                light_modes = light_state.attributes.get("supported_color_modes", [])
                for mode in light_modes:
                    if mode == "color_temp":
                        supported_modes.add(ColorMode.COLOR_TEMP)
                    elif mode in ["rgb", "rgbw", "rgbww"]:
                        supported_modes.add(ColorMode.RGB)
                    elif mode == "brightness":
                        supported_modes.add(ColorMode.BRIGHTNESS)
        
        # Always support brightness as minimum
        if not supported_modes:
            supported_modes.add(ColorMode.BRIGHTNESS)
            
        return supported_modes

    def _get_preferred_color_mode(self) -> ColorMode:
        """Get the preferred color mode for circadian lighting."""
        if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return ColorMode.COLOR_TEMP
        elif ColorMode.RGB in self._attr_supported_color_modes:
            return ColorMode.RGB
        else:
            return ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool:
        """Return true if any controlled light is on."""
        for light_id in self._controlled_lights:
            light_state = self.hass.states.get(light_id)
            if light_state and light_state.state == "on":
                return True
        return False

    @property
    def brightness(self) -> Optional[int]:
        """Return current brightness."""
        if not self.coordinator.data:
            return None
        
        lighting_values = self.coordinator.data.get("lighting_values", {})
        brightness_pct = lighting_values.get("brightness", 100)
        return int(brightness_pct * 2.55)  # Convert percentage to 0-255

    @property
    def color_temp(self) -> Optional[int]:
        """Return current color temperature."""
        if not self.coordinator.data:
            return None
        
        lighting_values = self.coordinator.data.get("lighting_values", {})
        return lighting_values.get("color_temp")

    @property
    def rgb_color(self) -> Optional[tuple[int, int, int]]:
        """Return RGB color if using RGB mode."""
        if self._attr_color_mode != ColorMode.RGB:
            return None
        
        # Convert color temp to RGB for circadian lighting
        color_temp = self.color_temp
        if color_temp:
            return self._color_temp_to_rgb(color_temp)
        return None

    def _color_temp_to_rgb(self, color_temp: int) -> tuple[int, int, int]:
        """Convert color temperature to RGB values."""
        # Simplified color temp to RGB conversion for circadian lighting
        if color_temp <= 3000:
            # Warm white - more red/orange
            return (255, 147, 41)
        elif color_temp <= 4000:
            # Neutral warm
            return (255, 197, 143)
        elif color_temp <= 5000:
            # Neutral
            return (255, 214, 170)
        else:
            # Cool white - more blue
            return (255, 244, 229)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            ATTR_CIRCADIAN_ENABLED: self._circadian_enabled,
            ATTR_CONTROLLED_LIGHTS: self._controlled_lights,
            ATTR_OVERRIDDEN: self._overridden,
        }
        
        if self.coordinator.data:
            data = self.coordinator.data
            attributes.update({
                ATTR_CURRENT_PHASE: data.get("current_phase"),
                "next_transition": data.get("next_transition"),
                "sunset_adjusted": data.get("sunset_adjusted"),
            })
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light group with circadian values."""
        if not self._circadian_enabled:
            # Just turn on lights without circadian adjustment
            await self._turn_on_controlled_lights(**kwargs)
            return
        
        # Get current circadian values
        lighting_values = {}
        if self.coordinator.data:
            lighting_values = self.coordinator.data.get("lighting_values", {})
        
        # Prepare service data with circadian values
        service_data = {}
        
        # Use provided values or circadian values
        if ATTR_BRIGHTNESS in kwargs:
            service_data["brightness"] = kwargs[ATTR_BRIGHTNESS]
        elif lighting_values.get("brightness"):
            service_data["brightness_pct"] = lighting_values["brightness"]
        
        if ATTR_COLOR_TEMP in kwargs:
            service_data["color_temp"] = kwargs[ATTR_COLOR_TEMP]
        elif lighting_values.get("color_temp") and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            service_data["color_temp"] = lighting_values["color_temp"]
        
        if ATTR_RGB_COLOR in kwargs:
            service_data["rgb_color"] = kwargs[ATTR_RGB_COLOR]
            
        if ATTR_TRANSITION in kwargs:
            service_data["transition"] = kwargs[ATTR_TRANSITION]
        elif lighting_values.get("transition"):
            service_data["transition"] = lighting_values["transition"]
        
        # Turn on all controlled lights with circadian values
        await self._turn_on_controlled_lights(**service_data)
        
        _LOGGER.info("LumaFlow light %s turned on with circadian values: %s", 
                    self.name, service_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off all controlled lights."""
        for light_id in self._controlled_lights:
            try:
                await self.hass.services.async_call(
                    "light", "turn_off", 
                    {"entity_id": light_id, **kwargs}, 
                    blocking=True
                )
            except Exception as err:
                _LOGGER.warning("Failed to turn off light %s: %s", light_id, err)
        
        _LOGGER.info("LumaFlow light %s turned off", self.name)

    async def _turn_on_controlled_lights(self, **kwargs: Any) -> None:
        """Turn on all controlled lights with given parameters."""
        for light_id in self._controlled_lights:
            service_data = {"entity_id": light_id, **kwargs}
            
            try:
                await self.hass.services.async_call(
                    "light", "turn_on", service_data, blocking=True
                )
            except Exception as err:
                _LOGGER.warning("Failed to turn on light %s: %s", light_id, err)

    @callback
    def enable_circadian(self) -> None:
        """Enable circadian behavior for this light."""
        self._circadian_enabled = True
        self._overridden = False
        _LOGGER.info("Circadian enabled for %s", self.name)

    @callback
    def disable_circadian(self) -> None:
        """Disable circadian behavior for this light."""
        self._circadian_enabled = False
        _LOGGER.info("Circadian disabled for %s", self.name)

    @callback
    def set_override(self, overridden: bool = True) -> None:
        """Mark this light as manually overridden."""
        self._overridden = overridden
        if overridden:
            _LOGGER.debug("Light %s marked as overridden", self.name)
        else:
            _LOGGER.debug("Light %s override cleared", self.name)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "LumaFlow",
            "manufacturer": "LumaFlow",
            "entry_type": "service",
        } 