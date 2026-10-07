"""The LumaFlow switch: on means lights follow the curve, off leaves them alone."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .controller import LumaFlowController
from .entity import LumaFlowEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([LumaFlowSwitch(hass.data[DOMAIN][entry.entry_id])])


class LumaFlowSwitch(LumaFlowEntity, SwitchEntity, RestoreEntity):
    _attr_name = None   # the device's own name, so the first entry is switch.lumaflow
    _attr_icon = "mdi:weather-sunset"

    def __init__(self, controller: LumaFlowController) -> None:
        super().__init__(controller, "switch")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == STATE_OFF:
            self.controller.enabled = False   # stays off across restarts

    @property
    def is_on(self) -> bool:
        return self.controller.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c = self.controller
        lights = c.lights()
        window = c.fade_window()
        return {
            "mode": c.mode,
            "controlled_lights": lights,
            "lights_on": [e for e in lights if c._is_on(e)],  # noqa: SLF001
            "overridden_lights": sorted(c.overridden),
            # Lights LumaFlow is fading on right now. An automation that resets bulbs when they're
            # switched on can skip these: {{ trigger.entity_id in state_attr('switch.lumaflow', 'fading_lights') }}
            "fading_lights": sorted(c.fading),
            "fade_in_start": window[0].isoformat() if window else None,
            "fade_in_end": window[1].isoformat() if window else None,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.controller.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.controller.async_set_enabled(False)
