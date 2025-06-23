"""Switch platform for LumaFlow."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SWITCH_ENTITY_ID
from .coordinator import LumaFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LumaFlow switch platform."""
    coordinator: LumaFlowCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities([LumaFlowSwitch(coordinator, config_entry)])


class LumaFlowSwitch(CoordinatorEntity[LumaFlowCoordinator], SwitchEntity):
    """Switch to enable/disable LumaFlow."""

    def __init__(
        self,
        coordinator: LumaFlowCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SWITCH_ENTITY_ID}"
        self._attr_name = "LumaFlow"
        self._attr_icon = "mdi:weather-sunset"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data.get("enabled", False) if self.coordinator.data else False

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        data = self.coordinator.data
        attributes = {
            "current_phase": data.get("current_phase"),
            "lights_count": len(self.coordinator.lights),
            "overridden_lights_count": len(data.get("overridden_lights", [])),
        }
        
        # Add lighting values if available
        lighting_values = data.get("lighting_values", {})
        if lighting_values:
            attributes.update({
                "current_brightness": lighting_values.get("brightness"),
                "current_color_temp": lighting_values.get("color_temp"),
                "transition_time": lighting_values.get("transition"),
            })
        
        # Add sunset/sunrise times if available
        sun_times = data.get("sun_times", {})
        if sun_times:
            attributes.update({
                "sunrise": sun_times.get("sunrise"),
                "sunset": sun_times.get("sunset"),
                "sunset_adjusted": data.get("sunset_adjusted"),
            })
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.coordinator.enable()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.coordinator.disable()
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "LumaFlow",
            "manufacturer": "LumaFlow",
            "entry_type": "service",
        } 