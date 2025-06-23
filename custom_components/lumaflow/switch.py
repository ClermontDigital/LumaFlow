"""Switch platform for LumaFlow - individual light controls."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_LIGHTS
from .coordinator import LumaFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LumaFlow switch platform."""
    coordinator: LumaFlowCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create individual switches for each controlled light
    switches = []
    for light_entity_id in coordinator.controlled_lights:
        switches.append(LumaFlowLightSwitch(coordinator, config_entry, light_entity_id))
    
    if switches:
        async_add_entities(switches)


class LumaFlowLightSwitch(CoordinatorEntity[LumaFlowCoordinator], SwitchEntity):
    """Switch to enable/disable individual lights in the LumaFlow group."""

    def __init__(
        self,
        coordinator: LumaFlowCoordinator,
        config_entry: ConfigEntry,
        light_entity_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._light_entity_id = light_entity_id
        self._group_name = coordinator.group_name
        
        # Get friendly name of the light
        light_state = coordinator.hass.states.get(light_entity_id)
        light_friendly_name = light_state.attributes.get("friendly_name", light_entity_id) if light_state else light_entity_id
        
        self._attr_unique_id = f"{config_entry.entry_id}_{light_entity_id.replace('.', '_')}_enabled"
        self._attr_name = f"{light_friendly_name} (LumaFlow)"
        self._attr_icon = "mdi:lightbulb"
        
        # Default to enabled
        self._enabled = True

    @property
    def is_on(self) -> bool:
        """Return true if light is enabled in LumaFlow group."""
        return self._enabled

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            "light_entity_id": self._light_entity_id,
            "group_name": self._group_name,
        }
        
        # Add current light status
        light_state = self.hass.states.get(self._light_entity_id)
        if light_state:
            attributes.update({
                "light_state": light_state.state,
                "light_brightness": light_state.attributes.get("brightness"),
                "light_color_temp": light_state.attributes.get("color_temp"),
            })
        
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable this light in the LumaFlow group."""
        self._enabled = True
        self.async_write_ha_state()
        _LOGGER.info("Enabled %s in LumaFlow group %s", self._light_entity_id, self._group_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable this light in the LumaFlow group."""
        self._enabled = False
        self.async_write_ha_state()
        _LOGGER.info("Disabled %s in LumaFlow group %s", self._light_entity_id, self._group_name)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, f"{self._config_entry.entry_id}_{self._group_name}")},
            "name": f"LumaFlow {self._group_name.title()}",
            "manufacturer": "LumaFlow",
            "entry_type": "service",
        } 