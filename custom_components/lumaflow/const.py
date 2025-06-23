"""Constants for LumaFlow integration."""

from homeassistant.const import Platform

DOMAIN = "lumaflow"
NAME = "LumaFlow"
VERSION = "0.2.0"

# Platforms
PLATFORMS = [Platform.LIGHT, Platform.SENSOR]

# Configuration keys
CONF_LIGHTS = "lights"
CONF_LIGHT_GROUPS = "light_groups"
CONF_GROUP_NAME = "group_name"
CONF_SUNSET_OFFSET = "sunset_offset"
CONF_TRANSITION_SPEED = "transition_speed"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_MAX_BRIGHTNESS = "max_brightness"
CONF_MIN_COLOR_TEMP = "min_color_temp"
CONF_MAX_COLOR_TEMP = "max_color_temp"
CONF_ENABLE_OVERRIDE_DETECTION = "enable_override_detection"
CONF_RESTORE_ON_STARTUP = "restore_on_startup"

# Default values
DEFAULT_SUNSET_OFFSET = 0  # minutes
DEFAULT_TRANSITION_SPEED = "moderate"
DEFAULT_MIN_BRIGHTNESS = 1
DEFAULT_MAX_BRIGHTNESS = 100
DEFAULT_MIN_COLOR_TEMP = 2700  # Warm white
DEFAULT_MAX_COLOR_TEMP = 6500  # Cool white
DEFAULT_ENABLE_OVERRIDE_DETECTION = True
DEFAULT_RESTORE_ON_STARTUP = True

# Transition speeds
TRANSITION_SPEEDS = {
    "slow": 300,     # 5 minutes
    "moderate": 180, # 3 minutes
    "fast": 60,      # 1 minute
}

# Circadian phases
PHASE_DAY = "day"
PHASE_SUNSET = "sunset"
PHASE_EVENING = "evening"
PHASE_NIGHT = "night"
PHASE_SUNRISE = "sunrise"

# Entity IDs
SENSOR_CURRENT_PHASE = "lumaflow_current_phase"
SENSOR_NEXT_TRANSITION = "lumaflow_next_transition"

# Service names
SERVICE_ENABLE = "enable"
SERVICE_DISABLE = "disable"
SERVICE_RESTORE_LIGHTS = "restore_lights"
SERVICE_OVERRIDE_LIGHTS = "override_lights"

# Attributes
ATTR_LIGHTS = "lights"
ATTR_BRIGHTNESS = "brightness"
ATTR_COLOR_TEMP = "color_temp"
ATTR_RGB_COLOR = "rgb_color"
ATTR_TRANSITION = "transition"
ATTR_CIRCADIAN_ENABLED = "circadian_enabled"
ATTR_CURRENT_PHASE = "current_phase"
ATTR_OVERRIDDEN = "overridden"
ATTR_CONTROLLED_LIGHTS = "controlled_lights" 