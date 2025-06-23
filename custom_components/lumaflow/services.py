"""Services for LumaFlow integration."""

import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_ENABLE,
    SERVICE_DISABLE,
    SERVICE_RESTORE_LIGHTS,
    SERVICE_OVERRIDE_LIGHTS,
    ATTR_LIGHTS,
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
)

_LOGGER = logging.getLogger(__name__)

# Service schemas
ENABLE_SERVICE_SCHEMA = vol.Schema({})

DISABLE_SERVICE_SCHEMA = vol.Schema({})

RESTORE_LIGHTS_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_LIGHTS): cv.entity_ids,
})

OVERRIDE_LIGHTS_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_LIGHTS): cv.entity_ids,
    vol.Optional(ATTR_BRIGHTNESS): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(ATTR_COLOR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=2000, max=6500)),
    vol.Optional(ATTR_RGB_COLOR): vol.All(list, vol.Length(min=3, max=3)),
})


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for LumaFlow."""
    
    async def async_enable_service(call: ServiceCall) -> None:
        """Handle enable service call."""
        _LOGGER.debug("Enable service called")
        
        # Enable all LumaFlow light entities
        for entity_id in hass.states.async_entity_ids("light"):
            if "_lumaflow" in entity_id:
                state = hass.states.get(entity_id)
                if state and hasattr(state, 'enable_circadian'):
                    await hass.async_add_executor_job(state.enable_circadian)
        
        # Also enable all coordinators
        for config_entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            await coordinator.async_request_refresh()
    
    async def async_disable_service(call: ServiceCall) -> None:
        """Handle disable service call."""
        _LOGGER.debug("Disable service called")
        
        # Disable all LumaFlow light entities
        for entity_id in hass.states.async_entity_ids("light"):
            if "_lumaflow" in entity_id:
                state = hass.states.get(entity_id)
                if state and hasattr(state, 'disable_circadian'):
                    await hass.async_add_executor_job(state.disable_circadian)
    
    async def async_restore_lights_service(call: ServiceCall) -> None:
        """Handle restore lights service call."""
        lights = call.data.get(ATTR_LIGHTS, [])
        _LOGGER.debug("Restore lights service called for: %s", lights)
        
        # Restore specified LumaFlow lights or all if none specified
        if not lights:
            # Restore all LumaFlow light entities
            lights = [entity_id for entity_id in hass.states.async_entity_ids("light") if "_lumaflow" in entity_id]
        
        for light_entity_id in lights:
            if "_lumaflow" in light_entity_id:
                # Enable circadian for LumaFlow entities
                state = hass.states.get(light_entity_id)
                if state and hasattr(state, 'enable_circadian'):
                    await hass.async_add_executor_job(state.enable_circadian)
                    # Turn on with circadian values
                    await hass.services.async_call(
                        "light", "turn_on", {"entity_id": light_entity_id}, blocking=True
                    )
    
    async def async_override_lights_service(call: ServiceCall) -> None:
        """Handle override lights service call."""
        lights = call.data[ATTR_LIGHTS]
        brightness = call.data.get(ATTR_BRIGHTNESS)
        color_temp = call.data.get(ATTR_COLOR_TEMP)
        rgb_color = call.data.get(ATTR_RGB_COLOR)
        
        _LOGGER.debug("Override lights service called for: %s", lights)
        
        # Apply override to specified lights
        for light_entity_id in lights:
            service_data = {"entity_id": light_entity_id}
            
            if brightness is not None:
                service_data["brightness_pct"] = brightness
            if color_temp is not None:
                service_data["color_temp"] = color_temp
            if rgb_color is not None:
                service_data["rgb_color"] = rgb_color
            
            try:
                # Turn on light with override settings
                await hass.services.async_call(
                    "light", "turn_on", service_data, blocking=True
                )
                
                # If it's a LumaFlow entity, mark as overridden
                if "_lumaflow" in light_entity_id:
                    state = hass.states.get(light_entity_id)
                    if state and hasattr(state, 'set_override'):
                        await hass.async_add_executor_job(state.set_override, True)
                        
            except Exception as err:
                _LOGGER.error("Failed to override light %s: %s", light_entity_id, err)
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_ENABLE,
        async_enable_service,
        schema=ENABLE_SERVICE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISABLE,
        async_disable_service,
        schema=DISABLE_SERVICE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTORE_LIGHTS,
        async_restore_lights_service,
        schema=RESTORE_LIGHTS_SERVICE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_OVERRIDE_LIGHTS,
        async_override_lights_service,
        schema=OVERRIDE_LIGHTS_SERVICE_SCHEMA,
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Unload services for LumaFlow."""
    hass.services.async_remove(DOMAIN, SERVICE_ENABLE)
    hass.services.async_remove(DOMAIN, SERVICE_DISABLE)
    hass.services.async_remove(DOMAIN, SERVICE_RESTORE_LIGHTS)
    hass.services.async_remove(DOMAIN, SERVICE_OVERRIDE_LIGHTS) 