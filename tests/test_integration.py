"""LumaFlow against fake lights: which lights it commands, overrides, groups, services and setup."""
from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, async_mock_service

from custom_components.lumaflow.const import DOMAIN
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.util import dt as dt_util

CT = {"supported_color_modes": ["color_temp"], "color_mode": "color_temp", "min_color_temp_kelvin": 3000,
      "max_color_temp_kelvin": 6000, "brightness": 255, "color_temp_kelvin": 6000, "supported_features": 32}
RGB = {"supported_color_modes": ["hs"], "color_mode": "hs", "brightness": 255, "supported_features": 0}
ONOFF = {"supported_color_modes": ["onoff"], "color_mode": "onoff"}


@pytest.fixture
async def lights(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    # 21:00 in the test instance's time zone: a couple of hours into the evening wind-down.
    freezer.move_to(dt_util.as_utc(datetime(2026, 10, 10, 21, 0, tzinfo=dt_util.get_time_zone(hass.config.time_zone))))
    hass.states.async_set("light.ct", "on", CT)
    hass.states.async_set("light.rgb", "on", RGB)
    hass.states.async_set("light.off", "off", CT)
    hass.states.async_set("light.onoff", "on", ONOFF)
    hass.states.async_set("light.group", "on", {"entity_id": ["light.ct", "light.rgb"], **CT})
    return async_mock_service(hass, "light", "turn_on")


async def _setup(hass, lights_conf, **options) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="LumaFlow", data={"lights": lights_conf}, options=options)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _sent(calls) -> dict:
    out = {}
    for c in calls:
        ids = c.data["entity_id"]
        for entity_id in ids if isinstance(ids, list) else [ids]:
            out[entity_id] = c.data
    return out


async def test_entities_and_only_on_dimmable_lights(hass, lights):
    await _setup(hass, ["light.ct", "light.rgb", "light.off", "light.onoff"])
    assert hass.states.get("switch.lumaflow").state == "on"
    assert hass.states.get("sensor.lumaflow_current_phase").state == "evening"
    assert hass.states.get("sensor.lumaflow_next_transition").state not in ("unknown", "unavailable")
    sent = _sent(lights)
    assert set(sent) == {"light.ct", "light.rgb"}
    attrs = hass.states.get("sensor.lumaflow_current_phase").attributes
    assert sent["light.ct"]["brightness_pct"] == attrs["brightness_pct"]
    assert 3000 <= sent["light.ct"]["color_temp_kelvin"] <= 6000      # clamped to the bulb's range
    assert sent["light.ct"]["transition"] == 180
    assert "rgb_color" in sent["light.rgb"] and "transition" not in sent["light.rgb"]


async def test_groups_are_controlled_member_by_member(hass, lights):
    await _setup(hass, ["light.group"])
    assert set(_sent(lights)) == {"light.ct", "light.rgb"}


async def test_switched_on_light_adapts_at_once(hass, lights):
    await _setup(hass, ["light.off"])
    assert not lights
    hass.states.async_set("light.off", "on", CT)
    await hass.async_block_till_done()
    assert _sent(lights)["light.off"]["transition"] == 1


async def test_manual_change_is_respected_until_restored(hass, lights, freezer):
    await _setup(hass, ["light.ct"])
    lights.clear()
    # Someone dims the lamp by hand (a context that isn't LumaFlow's).
    hass.states.async_set("light.ct", "on", {**CT, "brightness": 10}, context=Context())
    await hass.async_block_till_done()
    assert hass.states.get("switch.lumaflow").attributes["overridden_lights"] == ["light.ct"]
    freezer.tick(3600)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not lights   # left alone, even though the curve moved on
    await hass.services.async_call(DOMAIN, "restore_lights", {"lights": ["light.ct"]}, blocking=True)
    await hass.async_block_till_done()
    assert "light.ct" in _sent(lights)
    assert hass.states.get("switch.lumaflow").attributes["overridden_lights"] == []


async def test_own_updates_are_not_overrides(hass, lights):
    await _setup(hass, ["light.ct"])
    call = lights[-1]
    # The bulb reports back what LumaFlow asked for, under LumaFlow's own context.
    hass.states.async_set("light.ct", "on", {**CT, "brightness": 3}, context=call.context)
    await hass.async_block_till_done()
    assert hass.states.get("switch.lumaflow").attributes["overridden_lights"] == []


async def test_switch_off_stops_adjusting(hass, lights, freezer):
    await _setup(hass, ["light.ct"])
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.lumaflow"}, blocking=True)
    lights.clear()
    freezer.tick(3600)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not lights
    await hass.services.async_call(DOMAIN, "enable", {}, blocking=True)
    await hass.async_block_till_done()
    assert "light.ct" in _sent(lights)


async def test_override_service_sets_and_holds(hass, lights):
    await _setup(hass, ["light.ct"])
    lights.clear()
    await hass.services.async_call(DOMAIN, "override_lights", {"lights": ["light.ct"], "brightness": 40, "color_temp": 3500},
                                   blocking=True)
    await hass.async_block_till_done()
    assert _sent(lights)["light.ct"]["brightness_pct"] == 40
    assert _sent(lights)["light.ct"]["color_temp_kelvin"] == 3500
    assert hass.states.get("switch.lumaflow").attributes["overridden_lights"] == ["light.ct"]


async def test_old_entities_are_removed(hass, lights):
    entry = MockConfigEntry(domain=DOMAIN, title="LumaFlow", data={"lights": ["light.ct"]})
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create("light", DOMAIN, f"{entry.entry_id}_circadian_lumaflow", config_entry=entry)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert not [e for e in er.async_entries_for_config_entry(registry, entry.entry_id) if e.domain == "light"]


async def test_config_flow_three_steps(hass, lights):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"name": "Bedroom", "lights": ["light.ct"]})
    assert r["step_id"] == "timing"
    bad = await hass.config_entries.flow.async_configure(r["flow_id"], {
        "sunset_offset": 0, "transition_speed": "fast", "min_brightness": 80, "max_brightness": 20,
        "min_color_temp": 2700, "max_color_temp": 6500})
    assert bad["errors"] == {"min_brightness": "min_above_max"}
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {
        "sunset_offset": -30, "transition_speed": "fast", "min_brightness": 5, "max_brightness": 90,
        "min_color_temp": 2400, "max_color_temp": 5000})
    assert r["step_id"] == "advanced"
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"enable_override_detection": True, "restore_on_startup": False})
    assert r["type"] == "create_entry" and r["title"] == "Bedroom"
    assert r["data"]["lights"] == ["light.ct"] and r["data"]["max_color_temp"] == 5000


def _sunset(hass) -> datetime:
    return dt_util.as_local(get_astral_event_date(hass, "sunset", datetime(2026, 10, 10).date()))


def _call_for(calls, entity_id):
    return next(c for c in reversed(calls) if entity_id in (c.data["entity_id"] if isinstance(c.data["entity_id"], list) else [c.data["entity_id"]]))


async def _tick(hass, freezer, minutes):
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_fade_on_to_a_set_level_before_sunset(hass, freezer):
    sunset = _sunset(hass)
    freezer.move_to(sunset - timedelta(minutes=30))
    hass.states.async_set("light.rgb_off", "off", RGB)
    hass.states.async_set("light.ct_off", "off", CT)
    hass.states.async_set("light.already_on", "on", RGB)
    calls = async_mock_service(hass, "light", "turn_on")
    await _setup(hass, ["light.rgb_off", "light.ct_off", "light.already_on"], mode="fade_in",
                 fade_in_minutes=60, fade_in_brightness=50, fade_in_color="white")
    sent = _sent(calls)
    assert set(sent) == {"light.rgb_off", "light.ct_off"}          # the one already on is left alone
    assert sent["light.rgb_off"]["brightness_pct"] == 25           # halfway through the hour
    assert tuple(sent["light.rgb_off"]["rgb_color"]) == (255, 255, 255)
    assert sent["light.ct_off"]["color_temp_kelvin"] == 4000 and "transition" not in sent["light.ct_off"]
    sw = hass.states.get("switch.lumaflow").attributes
    assert sw["mode"] == "fade_in" and sw["fading_lights"] == ["light.ct_off", "light.rgb_off"]

    # The bulbs come on with what LumaFlow asked for: that's not a manual change.
    for e, attrs in (("light.rgb_off", RGB), ("light.ct_off", CT)):
        hass.states.async_set(e, "on", {**attrs, "brightness": 64}, context=_call_for(calls, e).context)
    await hass.async_block_till_done()
    assert hass.states.get("switch.lumaflow").attributes["overridden_lights"] == []

    calls.clear()
    await _tick(hass, freezer, 15)
    assert 34 <= _sent(calls)["light.rgb_off"]["brightness_pct"] <= 39

    # Someone switches one off mid-fade: it stays off for the night.
    hass.states.async_set("light.rgb_off", "off", RGB, context=Context())
    await hass.async_block_till_done()
    calls.clear()
    await _tick(hass, freezer, 10)
    assert "light.rgb_off" not in _sent(calls)

    # At sunset the fade finishes on the set level, and then LumaFlow leaves the lights alone.
    calls.clear()
    await _tick(hass, freezer, 10)
    assert _sent(calls)["light.ct_off"]["brightness_pct"] == 50
    assert hass.states.get("switch.lumaflow").attributes["fading_lights"] == []
    calls.clear()
    await _tick(hass, freezer, 120)
    assert not calls


async def test_set_level_mode_does_nothing_outside_the_fade(hass, lights):
    await _setup(hass, ["light.ct", "light.off"], mode="fade_in")
    assert not lights   # 21:00, after sunset: on lights aren't dimmed and off lights stay off


async def test_circadian_with_fade_in_comes_up_to_the_curve(hass, freezer):
    sunset = _sunset(hass)
    freezer.move_to(sunset - timedelta(minutes=30))
    hass.states.async_set("light.ct_off", "off", CT)
    calls = async_mock_service(hass, "light", "turn_on")
    await _setup(hass, ["light.ct_off"], fade_in=True, fade_in_minutes=60)
    sent = _sent(calls)["light.ct_off"]
    assert sent["brightness_pct"] == 50 and sent["color_temp_kelvin"] == 6000   # half of the day value, bulb's max K


async def test_options_flow_switches_mode(hass, lights):
    entry = await _setup(hass, ["light.ct"])
    r = await hass.config_entries.options.async_init(entry.entry_id)
    r = await hass.config_entries.options.async_configure(r["flow_id"], {"lights": ["light.ct"], "mode": "fade_in"})
    assert r["step_id"] == "settings" and "fade_in_brightness" in str(r["data_schema"].schema)
    r = await hass.config_entries.options.async_configure(r["flow_id"], {
        "sunset_offset": 0, "fade_in_minutes": 60, "fade_in_brightness": 50, "fade_in_color": "white",
        "enable_override_detection": True, "restore_on_startup": True})
    assert r["type"] == "create_entry" and entry.options["mode"] == "fade_in" and entry.options["fade_in_brightness"] == 50
