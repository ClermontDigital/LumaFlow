"""Setup in three steps (lights, timing, advanced) and an options flow to change any of it later."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ENABLE_OVERRIDE_DETECTION, CONF_FADE_IN, CONF_FADE_IN_BRIGHTNESS, CONF_FADE_IN_COLOR, CONF_FADE_IN_MINUTES,
    CONF_LIGHTS, CONF_MAX_BRIGHTNESS, CONF_MAX_COLOR_TEMP, CONF_MIN_BRIGHTNESS, CONF_MIN_COLOR_TEMP, CONF_MODE,
    CONF_RESTORE_ON_STARTUP, CONF_SUNSET_OFFSET, CONF_TRANSITION_SPEED, DEFAULTS, DOMAIN, FADE_COLORS, MODE_CIRCADIAN,
    MODES, NAME, TRANSITION_SPEEDS,
)


def _lights_schema(values: dict[str, Any], with_name: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_name:
        fields[vol.Required(CONF_NAME, default=values.get(CONF_NAME, NAME))] = str
    fields[vol.Required(CONF_LIGHTS, default=values.get(CONF_LIGHTS, []))] = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="light", multiple=True))
    fields[vol.Required(CONF_MODE, default=values.get(CONF_MODE, MODE_CIRCADIAN))] = selector.SelectSelector(
        selector.SelectSelectorConfig(options=MODES, translation_key="mode"))
    return vol.Schema(fields)


PCT = selector.NumberSelector(selector.NumberSelectorConfig(min=1, max=100, step=1, unit_of_measurement="%",
                                                            mode=selector.NumberSelectorMode.SLIDER))


def _timing_schema(v: dict[str, Any]) -> vol.Schema:
    """Settings for the chosen mode: the curve and an optional fade-in, or just the fade-in."""
    kelvin = selector.NumberSelector(selector.NumberSelectorConfig(min=2000, max=6500, step=50, unit_of_measurement="K",
                                                                   mode=selector.NumberSelectorMode.BOX))
    fields: dict[Any, Any] = {
        vol.Required(CONF_SUNSET_OFFSET, default=v[CONF_SUNSET_OFFSET]): selector.NumberSelector(
            selector.NumberSelectorConfig(min=-120, max=120, step=5, unit_of_measurement="min",
                                          mode=selector.NumberSelectorMode.BOX)),
    }
    if v.get(CONF_MODE, MODE_CIRCADIAN) == MODE_CIRCADIAN:
        fields.update({
            vol.Required(CONF_TRANSITION_SPEED, default=v[CONF_TRANSITION_SPEED]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=list(TRANSITION_SPEEDS), translation_key="transition_speed")),
            vol.Required(CONF_MIN_BRIGHTNESS, default=v[CONF_MIN_BRIGHTNESS]): PCT,
            vol.Required(CONF_MAX_BRIGHTNESS, default=v[CONF_MAX_BRIGHTNESS]): PCT,
            vol.Required(CONF_MIN_COLOR_TEMP, default=v[CONF_MIN_COLOR_TEMP]): kelvin,
            vol.Required(CONF_MAX_COLOR_TEMP, default=v[CONF_MAX_COLOR_TEMP]): kelvin,
            vol.Required(CONF_FADE_IN, default=v[CONF_FADE_IN]): bool,
        })
    fields[vol.Required(CONF_FADE_IN_MINUTES, default=v[CONF_FADE_IN_MINUTES])] = selector.NumberSelector(
        selector.NumberSelectorConfig(min=5, max=180, step=5, unit_of_measurement="min", mode=selector.NumberSelectorMode.BOX))
    if v.get(CONF_MODE, MODE_CIRCADIAN) != MODE_CIRCADIAN:
        fields.update({
            vol.Required(CONF_FADE_IN_BRIGHTNESS, default=v[CONF_FADE_IN_BRIGHTNESS]): PCT,
            vol.Required(CONF_FADE_IN_COLOR, default=v[CONF_FADE_IN_COLOR]): selector.SelectSelector(
                selector.SelectSelectorConfig(options=FADE_COLORS, translation_key="fade_in_color")),
        })
    return vol.Schema(fields)


def _advanced_schema(v: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ENABLE_OVERRIDE_DETECTION, default=v[CONF_ENABLE_OVERRIDE_DETECTION]): bool,
        vol.Required(CONF_RESTORE_ON_STARTUP, default=v[CONF_RESTORE_ON_STARTUP]): bool,
    })


def _check_timing(user_input: dict[str, Any]) -> dict[str, str]:
    errors = {}
    if CONF_MIN_BRIGHTNESS in user_input and user_input[CONF_MIN_BRIGHTNESS] > user_input[CONF_MAX_BRIGHTNESS]:
        errors[CONF_MIN_BRIGHTNESS] = "min_above_max"
    if CONF_MIN_COLOR_TEMP in user_input and user_input[CONF_MIN_COLOR_TEMP] >= user_input[CONF_MAX_COLOR_TEMP]:
        errors[CONF_MIN_COLOR_TEMP] = "min_above_max"
    return errors


def _ints(user_input: dict[str, Any]) -> dict[str, Any]:
    return {k: int(v) if isinstance(v, float) else v for k, v in user_input.items()}


class LumaFlowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_LIGHTS]:
                errors[CONF_LIGHTS] = "no_lights"
            else:
                self._data.update(user_input)
                return await self.async_step_timing()
        return self.async_show_form(step_id="user", data_schema=_lights_schema(self._data, True), errors=errors)

    async def async_step_timing(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _ints(user_input)
            errors = _check_timing(user_input)
            if not errors:
                self._data.update(user_input)
                return await self.async_step_advanced()
        return self.async_show_form(step_id="timing", data_schema=_timing_schema({**DEFAULTS, **self._data}), errors=errors)

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data.update(user_input)
            name = self._data.pop(CONF_NAME, NAME) or NAME
            return self.async_create_entry(title=name, data=self._data)
        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema({**DEFAULTS, **self._data}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return LumaFlowOptionsFlow()


class LumaFlowOptionsFlow(OptionsFlow):
    """Everything from setup can be changed later; the entry reloads to apply it."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def _current(self) -> dict[str, Any]:
        return {**DEFAULTS, **self.config_entry.data, **self.config_entry.options, **self._data}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_LIGHTS]:
                errors[CONF_LIGHTS] = "no_lights"
            else:
                self._data.update(user_input)
                return await self.async_step_settings()
        return self.async_show_form(step_id="init", data_schema=_lights_schema(self._current(), False), errors=errors)

    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current = self._current()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _ints(user_input)
            errors = _check_timing(user_input)
            if not errors:
                return self.async_create_entry(title="", data={**current, **user_input})
        schema = vol.Schema({**_timing_schema(current).schema, **_advanced_schema(current).schema})
        return self.async_show_form(step_id="settings", data_schema=schema, errors=errors)
