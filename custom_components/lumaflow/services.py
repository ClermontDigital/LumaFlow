"""lumaflow.enable / disable / restore_lights / override_lights."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.light import ATTR_BRIGHTNESS_PCT, ATTR_COLOR_TEMP_KELVIN
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Context, HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_LIGHTS, ATTR_RGB_COLOR, DOMAIN, SERVICE_DISABLE, SERVICE_ENABLE,
    SERVICE_OVERRIDE_LIGHTS, SERVICE_RESTORE_LIGHTS,
)
from .controller import LumaFlowController

RESTORE_SCHEMA = vol.Schema({vol.Optional(ATTR_LIGHTS): cv.entity_ids})
OVERRIDE_SCHEMA = vol.Schema({
    vol.Required(ATTR_LIGHTS): cv.entity_ids,
    vol.Optional(ATTR_BRIGHTNESS): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional(ATTR_COLOR_TEMP): vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),   # Kelvin
    vol.Optional(ATTR_RGB_COLOR): vol.All(vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple)),
})


def _controllers(hass: HomeAssistant) -> list[LumaFlowController]:
    return [c for c in hass.data.get(DOMAIN, {}).values() if isinstance(c, LumaFlowController)]


@callback
def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ENABLE):
        return

    async def enable(call: ServiceCall) -> None:
        for c in _controllers(hass):
            await c.async_set_enabled(True)

    async def disable(call: ServiceCall) -> None:
        for c in _controllers(hass):
            await c.async_set_enabled(False)

    async def restore(call: ServiceCall) -> None:
        for c in _controllers(hass):
            await c.async_restore(call.data.get(ATTR_LIGHTS))

    async def override(call: ServiceCall) -> None:
        lights = call.data[ATTR_LIGHTS]
        for c in _controllers(hass):
            c.mark_overridden(lights)   # before the change, so it isn't mistaken for drift
        data: dict[str, Any] = {ATTR_ENTITY_ID: lights}
        if ATTR_BRIGHTNESS in call.data:
            data[ATTR_BRIGHTNESS_PCT] = call.data[ATTR_BRIGHTNESS]
        if ATTR_RGB_COLOR in call.data:
            data["rgb_color"] = call.data[ATTR_RGB_COLOR]
        elif ATTR_COLOR_TEMP in call.data:
            data[ATTR_COLOR_TEMP_KELVIN] = call.data[ATTR_COLOR_TEMP]
        await hass.services.async_call("light", "turn_on", data, blocking=True,
                                       context=Context(user_id=call.context.user_id, parent_id=call.context.id))

    hass.services.async_register(DOMAIN, SERVICE_ENABLE, enable)
    hass.services.async_register(DOMAIN, SERVICE_DISABLE, disable)
    hass.services.async_register(DOMAIN, SERVICE_RESTORE_LIGHTS, restore, schema=RESTORE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_OVERRIDE_LIGHTS, override, schema=OVERRIDE_SCHEMA)
