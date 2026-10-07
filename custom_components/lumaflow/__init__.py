"""LumaFlow: circadian rhythm lighting for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .controller import LumaFlowController
from .services import async_register_services

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# Entities this version creates; anything else registered to an entry is left over from 0.x.
CURRENT_UNIQUE_IDS = ("{}_switch", "{}_current_phase", "{}_next_transition")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _remove_old_entities(hass, entry)
    controller = LumaFlowController(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await controller.async_start()
    entry.async_on_unload(controller.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _remove_old_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """0.x made a wrapper light and a switch per light; they're not used any more."""
    registry = er.async_get(hass)
    keep = {pattern.format(entry.entry_id) for pattern in CURRENT_UNIQUE_IDS}
    for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
        if ent.unique_id not in keep:
            _LOGGER.info("LumaFlow: removing %s, left over from an older version", ent.entity_id)
            registry.async_remove(ent.entity_id)
