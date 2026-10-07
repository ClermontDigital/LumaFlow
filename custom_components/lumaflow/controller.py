"""Drives the configured lights along the circadian curve.

Rules, from the README:
- Only lights that are already on are touched. LumaFlow never turns a light on or off.
- A light that's switched on adapts straight away.
- A manual change (brightness or colour that LumaFlow didn't make) marks that light overridden,
  and LumaFlow leaves it alone until it's switched off and on again, it's restored with
  `lumaflow.restore_lights`, or midnight passes.
- Light groups are expanded and their members are controlled one by one.
"""
from __future__ import annotations

from collections import deque
from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_MAX_COLOR_TEMP_KELVIN,
    ATTR_MIN_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, EVENT_HOMEASSISTANT_STARTED, STATE_ON
from homeassistant.core import Context, CoreState, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.sun import get_astral_event_date, get_astral_location
from homeassistant.util import color as color_util
from homeassistant.util import dt as dt_util

from . import circadian
from .const import (
    CONF_ENABLE_OVERRIDE_DETECTION,
    CONF_LIGHTS,
    CONF_MAX_BRIGHTNESS,
    CONF_MAX_COLOR_TEMP,
    CONF_MIN_BRIGHTNESS,
    CONF_MIN_COLOR_TEMP,
    CONF_RESTORE_ON_STARTUP,
    CONF_SUNSET_OFFSET,
    CONF_TRANSITION_SPEED,
    DEFAULTS,
    MIN_STEP_BRIGHTNESS_PCT,
    MIN_STEP_KELVIN,
    OVERRIDE_BRIGHTNESS_PCT,
    OVERRIDE_KELVIN,
    SIGNAL_UPDATE,
    TRANSITION_SPEEDS,
    TURN_ON_TRANSITION,
    UPDATE_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

COLOR_MODES_RGB = {ColorMode.HS, ColorMode.XY, ColorMode.RGB, ColorMode.RGBW, ColorMode.RGBWW}
COLOR_MODES_DIMMABLE = COLOR_MODES_RGB | {ColorMode.COLOR_TEMP, ColorMode.BRIGHTNESS, ColorMode.WHITE}


def entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Settings for an entry: options win over the original setup data."""
    return {**DEFAULTS, **entry.data, **entry.options}


class LumaFlowController:
    """One per config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.enabled = True
        self.target: circadian.Target | None = None
        self.sun: circadian.SunDay | None = None
        self.overridden: set[str] = set()
        self._applied: dict[str, dict[str, Any]] = {}   # what LumaFlow last asked each light for
        self._contexts: deque[str] = deque(maxlen=200)  # ids of our own service calls
        self._unsubs: list = []
        self._unsub_lights = None

    # Settings ---------------------------------------------------------------------------------

    @property
    def config(self) -> dict[str, Any]:
        return entry_config(self.entry)

    @property
    def settings(self) -> circadian.Settings:
        c = self.config
        low_k, high_k = sorted((int(c[CONF_MIN_COLOR_TEMP]), int(c[CONF_MAX_COLOR_TEMP])))
        low_b, high_b = sorted((int(c[CONF_MIN_BRIGHTNESS]), int(c[CONF_MAX_BRIGHTNESS])))
        return circadian.Settings(int(c[CONF_SUNSET_OFFSET]), low_b, high_b, low_k, high_k)

    @property
    def configured(self) -> list[str]:
        return list(self.config.get(CONF_LIGHTS) or [])

    def lights(self) -> list[str]:
        """Configured lights with light groups expanded to their members."""
        out: list[str] = []
        seen: set[str] = set()

        def add(entity_id: str, depth: int = 0) -> None:
            if entity_id in seen or depth > 5:
                return
            seen.add(entity_id)
            state = self.hass.states.get(entity_id)
            members = state.attributes.get(ATTR_ENTITY_ID) if state else None
            if isinstance(members, (list, tuple)) and members:
                for member in members:
                    if member.startswith("light."):
                        add(member, depth + 1)
                return
            out.append(entity_id)

        for entity_id in self.configured:
            add(entity_id)
        return out

    # Lifecycle --------------------------------------------------------------------------------

    async def async_start(self) -> None:
        self.refresh_target()
        self._unsubs.append(async_track_time_interval(
            self.hass, self._tick, timedelta(seconds=UPDATE_INTERVAL_SECONDS)))
        self._unsubs.append(async_track_time_change(self.hass, self._midnight, hour=0, minute=0, second=1))
        self._watch_lights()
        if self.hass.state is CoreState.running:
            self._startup()
        else:
            self._unsubs.append(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, lambda _e: self._startup()))

    @callback
    def async_stop(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._unsub_lights:
            self._unsub_lights()
            self._unsub_lights = None

    @callback
    def _watch_lights(self) -> None:
        if self._unsub_lights:
            self._unsub_lights()
        watch = sorted(set(self.lights()) | set(self.configured))
        self._unsub_lights = async_track_state_change_event(self.hass, watch, self._light_changed) if watch else None

    @callback
    def _startup(self) -> None:
        # Groups only list their members once everything has loaded, so re-read them now.
        self._watch_lights()
        if self.config[CONF_RESTORE_ON_STARTUP]:
            self.hass.async_create_task(self.async_apply(force=True))
        else:
            # Leave lights as they are until they're switched off and on, or midnight.
            self.overridden |= {e for e in self.lights() if self._is_on(e)}
            self._notify()

    # The curve --------------------------------------------------------------------------------

    def _sun_day(self, day: date) -> circadian.SunDay:
        sunrise = get_astral_event_date(self.hass, "sunrise", day)
        sunset = get_astral_event_date(self.hass, "sunset", day)
        up = True
        if sunrise is None or sunset is None:
            location, elevation = get_astral_location(self.hass)
            noon = dt_util.start_of_local_day(day) + timedelta(hours=12)
            up = location.solar_elevation(noon, elevation) > 0
        local = lambda d: dt_util.as_local(d) if d else None  # noqa: E731
        return circadian.SunDay(local(sunrise), local(sunset), up)

    def refresh_target(self, now: datetime | None = None) -> circadian.Target:
        now = dt_util.as_local(now or dt_util.now())
        today = now.date()
        days = [self._sun_day(today + timedelta(days=i)) for i in (-1, 0, 1)]
        self.sun = days[1]
        self.target = circadian.target(now, days[0], days[1], days[2], self.settings)
        return self.target

    # Applying ----------------------------------------------------------------------------------

    def _is_on(self, entity_id: str) -> bool:
        state = self.hass.states.get(entity_id)
        return bool(state and state.state == STATE_ON)

    def _command(self, entity_id: str, target: circadian.Target) -> dict[str, Any] | None:
        """The light.turn_on data that puts one light on the curve, or None if it can't be dimmed."""
        state = self.hass.states.get(entity_id)
        if not state:
            return None
        modes = set(state.attributes.get(ATTR_SUPPORTED_COLOR_MODES) or [])
        if not modes & COLOR_MODES_DIMMABLE:
            return None   # on/off only
        data: dict[str, Any] = {ATTR_BRIGHTNESS_PCT: target.brightness}
        if ColorMode.COLOR_TEMP in modes:
            low = state.attributes.get(ATTR_MIN_COLOR_TEMP_KELVIN) or 2000
            high = state.attributes.get(ATTR_MAX_COLOR_TEMP_KELVIN) or 6500
            data[ATTR_COLOR_TEMP_KELVIN] = int(min(high, max(low, target.kelvin)))
        elif modes & COLOR_MODES_RGB:
            r, g, b = color_util.color_temperature_to_rgb(target.kelvin)
            data[ATTR_RGB_COLOR] = (round(r), round(g), round(b))
        return data

    def _needs_update(self, entity_id: str, data: dict[str, Any]) -> bool:
        last = self._applied.get(entity_id)
        if not last:
            return True
        if abs(last.get(ATTR_BRIGHTNESS_PCT, 0) - data.get(ATTR_BRIGHTNESS_PCT, 0)) >= MIN_STEP_BRIGHTNESS_PCT:
            return True
        if ATTR_COLOR_TEMP_KELVIN in data:
            return abs(last.get(ATTR_COLOR_TEMP_KELVIN, 0) - data[ATTR_COLOR_TEMP_KELVIN]) >= MIN_STEP_KELVIN
        if ATTR_RGB_COLOR in data:
            return last.get(ATTR_RGB_COLOR) != data[ATTR_RGB_COLOR]
        return False

    async def _send(self, entity_id: str, data: dict[str, Any], transition: float) -> None:
        state = self.hass.states.get(entity_id)
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES) or 0) if state else 0
        call = {ATTR_ENTITY_ID: entity_id, **data}
        if transition and features & LightEntityFeature.TRANSITION:
            call[ATTR_TRANSITION] = transition
        context = Context()
        self._contexts.append(context.id)
        self._applied[entity_id] = dict(data)
        try:
            await self.hass.services.async_call("light", "turn_on", call, blocking=False, context=context)
        except Exception:  # noqa: BLE001 - one bad light shouldn't stop the rest
            _LOGGER.warning("LumaFlow couldn't adjust %s", entity_id, exc_info=True)

    async def async_apply(self, force: bool = False, only: list[str] | None = None, transition: float | None = None) -> int:
        """Put every on, non-overridden light on the curve. Returns how many were sent a command."""
        if not self.enabled:
            return 0
        target = self.refresh_target()
        speed = TRANSITION_SPEEDS.get(self.config[CONF_TRANSITION_SPEED], 180)
        sent = 0
        for entity_id in only or self.lights():
            if entity_id in self.overridden or not self._is_on(entity_id):
                continue
            data = self._command(entity_id, target)
            if data and (force or self._needs_update(entity_id, data)):
                await self._send(entity_id, data, speed if transition is None else transition)
                sent += 1
        self._notify()
        return sent

    # Events -------------------------------------------------------------------------------------

    async def _tick(self, _now: datetime) -> None:
        await self.async_apply()

    async def _midnight(self, _now: datetime) -> None:
        # Overrides last for the day, then everything goes back on the curve.
        if self.overridden:
            _LOGGER.debug("LumaFlow: clearing overrides at midnight: %s", sorted(self.overridden))
        self.overridden.clear()
        await self.async_apply(force=True)

    def _ours(self, event: Event) -> bool:
        ctx = event.context
        return ctx.id in self._contexts or (ctx.parent_id is not None and ctx.parent_id in self._contexts)

    def _drifted(self, entity_id: str, new_attrs: dict[str, Any]) -> bool:
        """Has the light moved away from what LumaFlow last set, by more than rounding and lag?"""
        last = self._applied.get(entity_id)
        if not last:
            return False
        bri = new_attrs.get(ATTR_BRIGHTNESS)
        if bri is not None and ATTR_BRIGHTNESS_PCT in last:
            if abs(bri / 255 * 100 - last[ATTR_BRIGHTNESS_PCT]) > OVERRIDE_BRIGHTNESS_PCT:
                return True
        if ATTR_COLOR_TEMP_KELVIN in last:
            mode = new_attrs.get(ATTR_COLOR_MODE)
            if mode and mode != ColorMode.COLOR_TEMP:
                return True   # switched to a colour
            kelvin = new_attrs.get(ATTR_COLOR_TEMP_KELVIN)
            if kelvin is not None and abs(kelvin - last[ATTR_COLOR_TEMP_KELVIN]) > OVERRIDE_KELVIN:
                return True
        elif ATTR_RGB_COLOR in last:
            rgb = new_attrs.get(ATTR_RGB_COLOR)
            if rgb is not None and max(abs(a - b) for a, b in zip(rgb, last[ATTR_RGB_COLOR])) > 25:
                return True
        return False

    @callback
    def _light_changed(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        old, new = event.data.get("old_state"), event.data.get("new_state")
        if entity_id in self.configured and entity_id not in self.lights():
            # A group changed membership or came online: watch the members instead.
            self._watch_lights()
            return
        if new is None:
            return
        was_on = old is not None and old.state == STATE_ON
        if new.state != STATE_ON:
            self._applied.pop(entity_id, None)
            return
        if not was_on:
            # Just switched on: a fresh start, so any override from before is forgotten.
            self.overridden.discard(entity_id)
            self._applied.pop(entity_id, None)
            if self.enabled:
                self.hass.async_create_task(self.async_apply(force=True, only=[entity_id], transition=TURN_ON_TRANSITION))
            return
        if (self.enabled and self.config[CONF_ENABLE_OVERRIDE_DETECTION] and entity_id not in self.overridden
                and not self._ours(event) and self._drifted(entity_id, dict(new.attributes))):
            _LOGGER.debug("LumaFlow: %s was changed by hand, leaving it alone", entity_id)
            self.overridden.add(entity_id)
            self._notify()

    # Services -------------------------------------------------------------------------------------

    async def async_set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            await self.async_apply(force=True)
        self._notify()

    async def async_restore(self, lights: list[str] | None = None) -> None:
        mine = set(self.lights())
        chosen = mine if not lights else mine & set(lights)
        self.overridden -= chosen
        await self.async_apply(force=True, only=sorted(chosen), transition=TURN_ON_TRANSITION)

    def mark_overridden(self, lights: list[str]) -> None:
        self.overridden |= set(lights) & set(self.lights())
        self._notify()

    @callback
    def _notify(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry.entry_id))
