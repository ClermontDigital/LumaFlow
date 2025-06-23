"""LumaFlow coordinator for managing astronomical calculations and light state."""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from astral import LocationInfo
from astral.sun import sun
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LIGHTS,
    CONF_LIGHT_GROUPS,
    CONF_SUNSET_OFFSET,
    CONF_TRANSITION_SPEED,
    CONF_MIN_BRIGHTNESS,
    CONF_MAX_BRIGHTNESS,
    CONF_MIN_COLOR_TEMP,
    CONF_MAX_COLOR_TEMP,
    CONF_ENABLE_OVERRIDE_DETECTION,
    DEFAULT_SUNSET_OFFSET,
    DEFAULT_TRANSITION_SPEED,
    DEFAULT_MIN_BRIGHTNESS,
    DEFAULT_MAX_BRIGHTNESS,
    DEFAULT_MIN_COLOR_TEMP,
    DEFAULT_MAX_COLOR_TEMP,
    DOMAIN,
    PHASE_DAY,
    PHASE_SUNSET,
    PHASE_EVENING,
    PHASE_NIGHT,
    PHASE_SUNRISE,
    TRANSITION_SPEEDS,
)

_LOGGER = logging.getLogger(__name__)


class LumaFlowCoordinator(DataUpdateCoordinator):
    """Coordinator for LumaFlow data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._enabled = True
        self._overridden_lights: Dict[str, Dict[str, Any]] = {}
        self._last_calculated_values: Dict[str, Any] = {}
        self._last_reset_date: Optional[date] = None
        
        # Get configuration (prefer options over data for runtime changes)
        self.lights = entry.data.get(CONF_LIGHTS, [])
        self.light_groups = entry.data.get(CONF_LIGHT_GROUPS, [])
        self.sunset_offset = entry.options.get(CONF_SUNSET_OFFSET, entry.data.get(CONF_SUNSET_OFFSET, DEFAULT_SUNSET_OFFSET))
        self.transition_speed = entry.options.get(CONF_TRANSITION_SPEED, entry.data.get(CONF_TRANSITION_SPEED, DEFAULT_TRANSITION_SPEED))
        self.min_brightness = entry.data.get(CONF_MIN_BRIGHTNESS, DEFAULT_MIN_BRIGHTNESS)
        self.max_brightness = entry.data.get(CONF_MAX_BRIGHTNESS, DEFAULT_MAX_BRIGHTNESS)
        self.min_color_temp = entry.data.get(CONF_MIN_COLOR_TEMP, DEFAULT_MIN_COLOR_TEMP)
        self.max_color_temp = entry.data.get(CONF_MAX_COLOR_TEMP, DEFAULT_MAX_COLOR_TEMP)
        self.enable_override_detection = entry.options.get(CONF_ENABLE_OVERRIDE_DETECTION, entry.data.get(CONF_ENABLE_OVERRIDE_DETECTION, True))
        
        # Set up location for astronomical calculations
        self._setup_location()
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        
        # Listen for options updates
        entry.add_update_listener(self.async_options_updated)

    def _setup_location(self) -> None:
        """Set up location for astronomical calculations."""
        latitude = self.hass.config.latitude
        longitude = self.hass.config.longitude
        timezone = str(self.hass.config.time_zone)
        
        self.location = LocationInfo(
            name="Home",
            region="",
            timezone=timezone,
            latitude=latitude,
            longitude=longitude
        )
        
        _LOGGER.debug(
            "Location setup: lat=%s, lon=%s, tz=%s",
            latitude, longitude, timezone
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data."""
        try:
            now = dt_util.utcnow()
            today = now.date()
            
            # Check for daily override reset (per PRD requirement)
            if self._last_reset_date != today:
                if self._overridden_lights:
                    _LOGGER.info("Daily reset: clearing %d overridden lights", len(self._overridden_lights))
                    self._overridden_lights.clear()
                self._last_reset_date = today
            
            # Calculate astronomical times
            sun_times = sun(self.location.observer, date=today)
            
            # Apply sunset offset
            sunset_adjusted = sun_times["sunset"] + timedelta(minutes=self.sunset_offset)
            
            # Calculate current phase
            current_phase = self._calculate_current_phase(now, sun_times, sunset_adjusted)
            
            # Calculate lighting values based on current phase
            lighting_values = self._calculate_lighting_values(now, sun_times, sunset_adjusted)
            
            # Update lights if enabled and not overridden
            if self._enabled:
                await self._update_lights(lighting_values)
            
            return {
                "sun_times": sun_times,
                "sunset_adjusted": sunset_adjusted,
                "current_phase": current_phase,
                "lighting_values": lighting_values,
                "enabled": self._enabled,
                "overridden_lights": list(self._overridden_lights.keys()),
            }
            
        except Exception as err:
            raise UpdateFailed(f"Error updating LumaFlow data: {err}") from err

    def _calculate_current_phase(
        self, now: datetime, sun_times: Dict[str, datetime], sunset_adjusted: datetime
    ) -> str:
        """Calculate current circadian phase."""
        sunrise = sun_times["sunrise"]
        sunset = sun_times["sunset"]
        
        # Define phase boundaries
        if now < sunrise:
            phase = PHASE_NIGHT
        elif now < sunset_adjusted:
            phase = PHASE_DAY
        elif now < sunset_adjusted + timedelta(hours=1):
            phase = PHASE_SUNSET
        elif now < sunset_adjusted + timedelta(hours=4):
            phase = PHASE_EVENING
        else:
            phase = PHASE_NIGHT
            
        _LOGGER.debug("Phase calculation: now=%s, sunrise=%s, sunset=%s, sunset_adjusted=%s, phase=%s", 
                     now.strftime("%H:%M"), sunrise.strftime("%H:%M"), sunset.strftime("%H:%M"), 
                     sunset_adjusted.strftime("%H:%M"), phase)
        return phase

    def _calculate_lighting_values(
        self, now: datetime, sun_times: Dict[str, datetime], sunset_adjusted: datetime
    ) -> Dict[str, Any]:
        """Calculate lighting values based on time since sunset."""
        if now < sunset_adjusted:
            # Before sunset - use day values
            brightness = self.max_brightness
            color_temp = self.max_color_temp
            _LOGGER.debug("Daylight values: brightness=%s%%, color_temp=%sK", brightness, color_temp)
            
        else:
            # After sunset - calculate based on time elapsed
            time_since_sunset = (now - sunset_adjusted).total_seconds() / 3600  # hours
            
            # Calculate progression (0 = just after sunset, 1 = deep night)
            max_progression_hours = 4  # 4 hours to reach minimum values
            progression = min(time_since_sunset / max_progression_hours, 1.0)
            
            # Calculate brightness (linear decrease)
            brightness_range = self.max_brightness - self.min_brightness
            brightness = self.max_brightness - (brightness_range * progression)
            
            # Calculate color temperature (linear decrease to warmer)
            color_temp_range = self.max_color_temp - self.min_color_temp
            color_temp = self.max_color_temp - (color_temp_range * progression)
            
            _LOGGER.debug("Evening values: time_since_sunset=%.1fh, progression=%.2f, brightness=%s%%, color_temp=%sK", 
                         time_since_sunset, progression, int(brightness), int(color_temp))
        
        return {
            "brightness": int(brightness),
            "color_temp": int(color_temp),
            "transition": TRANSITION_SPEEDS.get(self.transition_speed, 180),
        }

    async def _update_lights(self, lighting_values: Dict[str, Any]) -> None:
        """Update light states with calculated values."""
        updated_lights = 0
        for light_entity_id in self.lights:
            if light_entity_id in self._overridden_lights:
                _LOGGER.debug("Skipping overridden light: %s", light_entity_id)
                continue  # Skip overridden lights
                
            light_state = self.hass.states.get(light_entity_id)
            if not light_state or light_state.state != "on":
                _LOGGER.debug("Skipping light %s (state: %s)", light_entity_id, light_state.state if light_state else "unavailable")
                continue  # Only update lights that are on
            
            # Prepare service data
            service_data = {
                "entity_id": light_entity_id,
                "brightness_pct": lighting_values["brightness"],
                "transition": lighting_values["transition"],
            }
            
            # Add color temperature if supported
            if self._light_supports_color_temp(light_entity_id):
                service_data["color_temp"] = lighting_values["color_temp"]
                _LOGGER.info("Updating light %s: brightness=%s%%, color_temp=%sK, transition=%ss", 
                            light_entity_id, lighting_values["brightness"], lighting_values["color_temp"], lighting_values["transition"])
            else:
                _LOGGER.info("Updating light %s: brightness=%s%%, transition=%ss (no color temp support)", 
                            light_entity_id, lighting_values["brightness"], lighting_values["transition"])
            
            try:
                await self.hass.services.async_call(
                    "light", "turn_on", service_data, blocking=True
                )
                updated_lights += 1
            except Exception as err:
                _LOGGER.warning(
                    "Failed to update light %s: %s", light_entity_id, err
                )
        
        if updated_lights > 0:
            _LOGGER.info("Updated %d lights with circadian values", updated_lights)

    def _light_supports_color_temp(self, entity_id: str) -> bool:
        """Check if light supports color temperature."""
        light_state = self.hass.states.get(entity_id)
        if not light_state:
            return False
        
        supported_color_modes = light_state.attributes.get("supported_color_modes", [])
        return "color_temp" in supported_color_modes

    @callback
    def enable(self) -> None:
        """Enable LumaFlow."""
        self._enabled = True
        _LOGGER.info("LumaFlow enabled")

    @callback
    def disable(self) -> None:
        """Disable LumaFlow."""
        self._enabled = False
        _LOGGER.info("LumaFlow disabled")

    @callback
    def add_override(self, entity_id: str, original_state: Dict[str, Any]) -> None:
        """Add light to override list."""
        self._overridden_lights[entity_id] = original_state
        _LOGGER.debug("Added override for %s", entity_id)

    @callback
    def remove_override(self, entity_id: str) -> None:
        """Remove light from override list."""
        if entity_id in self._overridden_lights:
            del self._overridden_lights[entity_id]
            _LOGGER.debug("Removed override for %s", entity_id)
    
    async def async_options_updated(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.debug("Options updated, refreshing configuration")
        
        # Update configuration from options
        self.sunset_offset = entry.options.get(CONF_SUNSET_OFFSET, entry.data.get(CONF_SUNSET_OFFSET, DEFAULT_SUNSET_OFFSET))
        self.transition_speed = entry.options.get(CONF_TRANSITION_SPEED, entry.data.get(CONF_TRANSITION_SPEED, DEFAULT_TRANSITION_SPEED))
        self.enable_override_detection = entry.options.get(CONF_ENABLE_OVERRIDE_DETECTION, entry.data.get(CONF_ENABLE_OVERRIDE_DETECTION, True))
        
        # Force a refresh to apply new settings
        await self.async_request_refresh() 