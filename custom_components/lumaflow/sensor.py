"""Sensor platform for LumaFlow."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_CURRENT_PHASE,
    SENSOR_NEXT_TRANSITION,
    PHASE_DAY,
    PHASE_SUNSET,
    PHASE_EVENING,
    PHASE_NIGHT,
    PHASE_SUNRISE,
)
from .coordinator import LumaFlowCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LumaFlow sensor platform."""
    coordinator: LumaFlowCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities([
        LumaFlowCurrentPhaseSensor(coordinator, config_entry),
        LumaFlowNextTransitionSensor(coordinator, config_entry),
    ])


class LumaFlowCurrentPhaseSensor(CoordinatorEntity[LumaFlowCoordinator], SensorEntity):
    """Sensor for current circadian phase."""

    def __init__(
        self,
        coordinator: LumaFlowCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_CURRENT_PHASE}"
        self._attr_name = "LumaFlow Current Phase"
        self._attr_icon = "mdi:weather-sunset"

    @property
    def native_value(self) -> Optional[str]:
        """Return the current phase."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("current_phase")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        data = self.coordinator.data
        lighting_values = data.get("lighting_values", {})
        
        return {
            "brightness": lighting_values.get("brightness"),
            "color_temp": lighting_values.get("color_temp"),
            "enabled": data.get("enabled", False),
            "lights_controlled": len(self.coordinator.lights),
            "overridden_lights": len(data.get("overridden_lights", [])),
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "LumaFlow",
            "manufacturer": "LumaFlow",
            "entry_type": "service",
        }


class LumaFlowNextTransitionSensor(CoordinatorEntity[LumaFlowCoordinator], SensorEntity):
    """Sensor for next transition time."""

    def __init__(
        self,
        coordinator: LumaFlowCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_{SENSOR_NEXT_TRANSITION}"
        self._attr_name = "LumaFlow Next Transition"
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_class = "timestamp"

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the next transition time."""
        if not self.coordinator.data:
            return None
        
        data = self.coordinator.data
        current_phase = data.get("current_phase")
        sun_times = data.get("sun_times", {})
        sunset_adjusted = data.get("sunset_adjusted")
        
        if not current_phase or not sun_times:
            return None
        
        # Calculate next transition based on current phase
        if current_phase == PHASE_DAY:
            return sunset_adjusted
        elif current_phase == PHASE_SUNSET:
            return sunset_adjusted + timedelta(hours=1)  # End of sunset phase
        elif current_phase == PHASE_EVENING:
            return sunset_adjusted + timedelta(hours=4)  # End of evening phase
        elif current_phase == PHASE_NIGHT:
            return sun_times.get("sunrise")
        elif current_phase == PHASE_SUNRISE:
            return sunset_adjusted  # Next sunset
        
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        data = self.coordinator.data
        sun_times = data.get("sun_times", {})
        
        attributes = {}
        if sun_times:
            attributes.update({
                "sunrise": sun_times.get("sunrise"),
                "sunset": sun_times.get("sunset"),
                "sunset_adjusted": data.get("sunset_adjusted"),
            })
        
        return attributes

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "LumaFlow",
            "manufacturer": "LumaFlow",
            "entry_type": "service",
        } 