"""Sensors: the current circadian phase and when the next phase starts."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import circadian
from .const import DOMAIN
from .controller import LumaFlowController
from .entity import LumaFlowEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    controller = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PhaseSensor(controller), NextTransitionSensor(controller)])


class PhaseSensor(LumaFlowEntity, SensorEntity):
    _attr_translation_key = "current_phase"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = circadian.PHASES
    _attr_icon = "mdi:theme-light-dark"

    def __init__(self, controller: LumaFlowController) -> None:
        super().__init__(controller, "current_phase")

    @property
    def native_value(self) -> str | None:
        return self.controller.target.phase if self.controller.target else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        c, t, sun = self.controller, self.controller.target, self.controller.sun
        if not t:
            return {}
        return {
            "brightness_pct": t.brightness,
            "color_temp_kelvin": t.kelvin,
            "progress": round(t.progress, 3),
            "sunrise": sun.sunrise.isoformat() if sun and sun.sunrise else None,
            "sunset": sun.sunset.isoformat() if sun and sun.sunset else None,
            "sunset_offset_minutes": c.settings.sunset_offset,
            "enabled": c.enabled,
            "overridden_lights": sorted(c.overridden),
        }


class NextTransitionSensor(LumaFlowEntity, SensorEntity):
    _attr_translation_key = "next_transition"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-outline"

    def __init__(self, controller: LumaFlowController) -> None:
        super().__init__(controller, "next_transition")

    @property
    def native_value(self) -> datetime | None:
        return self.controller.target.next_change if self.controller.target else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        t = self.controller.target
        return {"next_phase": t.next_phase} if t else {}
