"""Constants for LumaFlow."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "lumaflow"
NAME = "LumaFlow"

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]

# Configuration keys (unchanged since 0.1, so existing entries keep working)
CONF_LIGHTS = "lights"
CONF_GROUP_NAME = "group_name"          # 0.x only; the entry title is used now
CONF_SUNSET_OFFSET = "sunset_offset"
CONF_TRANSITION_SPEED = "transition_speed"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_MAX_BRIGHTNESS = "max_brightness"
CONF_MIN_COLOR_TEMP = "min_color_temp"  # Kelvin
CONF_MAX_COLOR_TEMP = "max_color_temp"  # Kelvin
CONF_ENABLE_OVERRIDE_DETECTION = "enable_override_detection"
CONF_RESTORE_ON_STARTUP = "restore_on_startup"

DEFAULTS = {
    CONF_SUNSET_OFFSET: 0,
    CONF_TRANSITION_SPEED: "moderate",
    CONF_MIN_BRIGHTNESS: 1,
    CONF_MAX_BRIGHTNESS: 100,
    CONF_MIN_COLOR_TEMP: 2700,
    CONF_MAX_COLOR_TEMP: 6500,
    CONF_ENABLE_OVERRIDE_DETECTION: True,
    CONF_RESTORE_ON_STARTUP: True,
}

# Seconds each scheduled adjustment fades over.
TRANSITION_SPEEDS = {"slow": 300, "moderate": 180, "fast": 60}
TURN_ON_TRANSITION = 1   # a light that's just been switched on adapts almost at once

UPDATE_INTERVAL_SECONDS = 60

# A light counts as manually changed when it drifts this far from what LumaFlow last set.
OVERRIDE_BRIGHTNESS_PCT = 5
OVERRIDE_KELVIN = 150
# Below this change, a scheduled update isn't worth a command to the light.
MIN_STEP_BRIGHTNESS_PCT = 1
MIN_STEP_KELVIN = 25

SERVICE_ENABLE = "enable"
SERVICE_DISABLE = "disable"
SERVICE_RESTORE_LIGHTS = "restore_lights"
SERVICE_OVERRIDE_LIGHTS = "override_lights"

ATTR_LIGHTS = "lights"
ATTR_BRIGHTNESS = "brightness"
ATTR_COLOR_TEMP = "color_temp"           # Kelvin, as in the README examples
ATTR_RGB_COLOR = "rgb_color"

SIGNAL_UPDATE = f"{DOMAIN}_update_{{}}"   # format with entry_id
