# LumaFlow - Circadian Rhythm Lighting for Home Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/ClermontDigital/LumaFlow/releases)

LumaFlow automatically adjusts your smart lights to follow natural circadian rhythms. It takes
sunrise and sunset from your Home Assistant location, keeps lights bright and cool through the day,
and dims and warms them through the evening. That supports your natural sleep-wake cycle without
you touching a thing.

> **1.0.0 is a rewrite.** Earlier versions didn't set up on current Home Assistant releases, and put
> lights on full daylight after midnight. If you tried LumaFlow before and it didn't work, this
> version is worth another go. Existing setups carry over. See the [changelog](#changelog).

## Core Capabilities

### 🌅 **Astronomical Synchronization**
- **Real-time calculations**: sunrise and sunset come from your Home Assistant location, recalculated every day
- **Seasonal adaptation**: follows the changing length of the day through the year
- **Works worldwide**: when the sun doesn't rise or set at all (polar day or night), LumaFlow holds the day or night values
- **Configurable timing**: a sunset offset from -120 to +120 minutes

### 🏠 **Intelligent Light Management**
- **Selective control**: only lights that are already on are adjusted. LumaFlow never turns a light on or off
- **Immediate adaptation**: when a light is turned on, it adopts the current values within about a second
- **Universal compatibility**: colour temperature lights, RGB lights (warm white is mixed from RGB) and brightness-only lights
- **Brand agnostic**: anything Home Assistant can dim works, including Hue, LIFX, Shelly, WLED, ESPHome, Tuya and Zigbee bulbs
- **Light groups**: each light in a group is adjusted on its own, within that light's colour temperature range

### 🎛️ **Advanced Override System**
- **Manual override detection**: change a light yourself, from a switch, an app or a scene, and LumaFlow leaves that light alone
- **Easy restore**: `lumaflow.restore_lights` puts it straight back on the curve
- **Fresh start**: switching a light off and on again also puts it back on the curve
- **Daily reset**: any overrides left over clear at midnight
- **Per-light**: an override only affects the light that was changed

### ⚙️ **Flexible Configuration**
- **Three-step setup** in the Home Assistant UI: lights, timing, advanced
- **Customisable ranges**: brightness (1–100%) and colour temperature (2000–6500 K)
- **Transition control**: slow (5 min), moderate (3 min) or fast (1 min) fades for each adjustment
- **Change anything later** in the integration's options

### 🤖 **Home Assistant Integration**
- **Native entities**: a switch and two sensors, for dashboards and automations
- **Services** for automations: enable, disable, restore and override
- **Status**: the current phase, today's sunrise and sunset, the target values and which lights are overridden

## How It Works

LumaFlow works out a target every minute. Rather than jumping between steps, the values move
continuously, so changes are smooth.

```
sunrise ─1 h─▶  day  ───────────▶ sunset+offset ─1 h─▶ evening ─3 h─▶ night ──────▶ next sunrise
  ramp up       brightest, coolest      winding down begins    dimming    dimmest, warmest
```

### 🔄 **Circadian Phases**

1. **Sunrise** (sunrise to +1 hour)
   - Brightness and colour temperature rise smoothly from the night values to the day values
   - **Purpose**: a gentle start instead of a sudden jump to full daylight

2. **Day** (+1 hour after sunrise to sunset + offset)
   - **Brightness**: the maximum configured level (default 100%)
   - **Colour temperature**: the coolest setting (default 6500 K)
   - **Purpose**: supports alertness and productivity during daylight hours

3. **Sunset** (sunset + offset to +1 hour)
   - **Brightness**: the gradual decrease begins
   - **Colour temperature**: starts warming from cool towards neutral
   - **Purpose**: signals the beginning of the evening wind-down

4. **Evening** (+1 to +4 hours after sunset + offset)
   - **Brightness**: decreases linearly to the minimum level
   - **Colour temperature**: progressively warms to amber tones
   - **Purpose**: prepares the body for sleep by reducing blue light

5. **Night** (+4 hours after sunset + offset until sunrise)
   - **Brightness**: the minimum configured level (default 1%)
   - **Colour temperature**: the warmest setting (default 2700 K)
   - **Purpose**: minimal lighting that doesn't disrupt sleep

From sunset + offset, brightness and colour temperature fall in a straight line over the four
hours to the night values. With a late summer sunset, that wind-down carries on past midnight.

### ⚡ **Smart Activation**
- **Selective control**: only lights that are on are adjusted
- **Instant adaptation**: a light that's turned on takes the current values straight away
- **Respects manual control**: lights you turn off stay off, and lights you adjust stay as you set them
- **Daily override reset**: manual adjustments clear at midnight
- **Small steps are skipped**: a light only gets a command when its target moves by at least 1% or 25 K, so it isn't flooded

## Scientific Foundation

### 🧬 **Circadian Science**
LumaFlow follows the principles used in circadian lighting research:

- **Blue light regulation**: gradually reduces blue light in the evening, to support natural melatonin production
- **Colour temperature progression**: mimics the natural change from daylight (6500 K) to firelight (2700 K)
- **Brightness dimming**: follows the natural fall in light intensity after sunset
- **Timing precision**: uses astronomical calculations rather than fixed schedules

### 💡 **Health Benefits**
- **Better sleep**: less blue light in the evening supports natural sleep-wake cycles
- **Better alertness**: bright, cool light during the productive hours of the day
- **Less eye strain**: gentle transitions instead of harsh changes
- **Mood support**: consistent light patterns can help regulate mood and energy

### 🏥 **Accessibility Features**
- **Customisable intensity**: set the brightness and colour ranges to suit your eyes
- **Gradual transitions**: no sudden changes
- **Manual override**: adjust a light whenever you need to, and LumaFlow respects it
- **Automatic reset**: back to healthy patterns every day without you doing anything

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository (category: Integration)
2. Install "LumaFlow" through HACS
3. Restart Home Assistant
4. Go to **Settings → Devices & services**
5. Click **Add integration** and search for "LumaFlow"

### Manual Installation

1. Download the latest release
2. Copy the `custom_components/lumaflow` folder into your Home Assistant `custom_components` folder
3. Restart Home Assistant
4. Add the integration through the UI

## Configuration

### Initial Setup

1. **Choose lights**: the lights (or light groups) LumaFlow should adjust. Any dimmable light can be
   chosen. Lights that can only switch on and off are ignored.

2. **Timing and ranges**:
   - **Sunset offset**: start winding down before (negative) or after sunset, from -120 to +120 minutes
   - **Transition speed**: how long each adjustment fades over (slow 5 min, moderate 3 min, fast 1 min)
   - **Night and day brightness**: from 1 to 100%
   - **Night and day colour temperature**: from 2000 to 6500 K. Each light is kept within its own range.

3. **Advanced**:
   - **Leave a light alone after it's changed by hand** (override detection)
   - **Put lights back on the curve when Home Assistant starts** (restore on startup). If this is off,
     lights that are on at startup are treated as overridden until they're switched off and on, or midnight.

Everything can be changed later under **Settings → Devices & services → LumaFlow → Configure**.
The integration reloads to apply the changes.

## Usage

### Basic Control

- **Enable/disable**: use the `switch.lumaflow` entity. Turning it off leaves the lights exactly as they are.
  The setting survives restarts.
- **Status**: `sensor.lumaflow_current_phase` and `sensor.lumaflow_next_transition`
- **Manual override**: adjust a light yourself and LumaFlow leaves it alone

### Services

#### `lumaflow.enable`
Turn circadian lighting on, and put every light that's on straight onto the curve.

#### `lumaflow.disable`
Stop adjusting lights. The settings are kept.

#### `lumaflow.restore_lights`
Clear manual overrides and put lights straight back on the curve.

```yaml
action: lumaflow.restore_lights
data:
  lights:  # Optional - leave out to restore every LumaFlow light
    - light.living_room
    - light.kitchen
```

#### `lumaflow.override_lights`
Set lights to your own values. LumaFlow leaves them alone until they're restored, switched off and
on again, or midnight passes.

```yaml
action: lumaflow.override_lights
data:
  lights:
    - light.living_room
  brightness: 50       # Optional, percent
  color_temp: 3000     # Optional, Kelvin
  rgb_color: [255, 200, 100]  # Optional
```

## Entities Created

The names below are for an entry called "LumaFlow". A second entry gets its own name.

- **Switch** `switch.lumaflow`: enable or disable. Its attributes list the controlled lights,
  which are on, and which are overridden.
- **Sensor** `sensor.lumaflow_current_phase`: `sunrise`, `day`, `sunset`, `evening` or `night`.
  Its attributes include the target brightness and colour temperature, today's sunrise and sunset,
  and the overridden lights.
- **Sensor** `sensor.lumaflow_next_transition`: when the next phase starts, with the
  `next_phase` attribute.

## Automation Examples

### Enable with Motion Detection

```yaml
automation:
  - alias: "Enable LumaFlow with Motion"
    triggers:
      - trigger: state
        entity_id: binary_sensor.living_room_motion
        to: "on"
    conditions:
      - condition: state
        entity_id: switch.lumaflow
        state: "off"
    actions:
      - action: lumaflow.enable
```

### Disable During Movie Time

```yaml
automation:
  - alias: "Disable LumaFlow for Movies"
    triggers:
      - trigger: state
        entity_id: media_player.tv
        to: "playing"
    actions:
      - action: lumaflow.disable

  - alias: "Re-enable LumaFlow After Movies"
    triggers:
      - trigger: state
        entity_id: media_player.tv
        from: "playing"
    actions:
      - action: lumaflow.enable
```

## Supported Light Types

| Light Type | Support Level | What LumaFlow sets |
|------------|---------------|--------------------|
| **Colour temperature** | Full | Colour temperature (within the bulb's range) and brightness |
| **RGB / HS / XY** | Full | A warm-to-cool white mixed from RGB, and brightness |
| **Brightness only** | Brightness | Brightness only |
| **On/off only** | None | Ignored |
| **Light groups** | Full | Each member individually |

## Technical Specifications

- **Home Assistant**: 2025.1 or newer
- **Dependencies**: none to install. Sun times come from Home Assistant's own sun calculations.
- **Update frequency**: every minute, plus immediately when a light turns on
- **Transitions**: only sent to lights that support them

## Troubleshooting

### 🚨 **Installation Issues**

#### Integration Won't Load
- Restart Home Assistant after installing or updating
- Check that the folder is `custom_components/lumaflow`, with `manifest.json` directly inside it
- Check **Settings → System → Logs** for lines mentioning `lumaflow`

### 🔧 **Configuration Problems**

#### Lights Not Responding to LumaFlow
1. Check `switch.lumaflow` is on
2. Check the light is on. LumaFlow never turns lights on.
3. Look at `overridden_lights` on the switch. If the light is listed, restore it or switch it off and on.
4. Check the light can be dimmed. On/off-only lights are ignored.
5. Look in the logs for "LumaFlow couldn't adjust"

#### A light keeps getting marked as overridden
Something other than LumaFlow is changing it: another automation, an adaptive lighting
integration, or a "turn on at this colour" rule. Remove that light from the other automation, or
turn off override detection in the options.

#### Incorrect Sunset/Sunrise Times
- Check the location and time zone under **Settings → System → General**
- Look at the `sunrise` and `sunset` attributes on `sensor.lumaflow_current_phase`

### 📋 **Diagnostic Information**
- `switch.lumaflow`: controlled lights, lights on, overridden lights
- `sensor.lumaflow_current_phase`: phase, target values, sunrise, sunset, offset
- `sensor.lumaflow_next_transition`: the next phase and when it starts

### 🆘 **Getting Help**
1. **Check the logs**: **Settings → System → Logs**
2. **Check the entities**: **Developer tools → States**, search for "lumaflow"
3. **Open an issue**: [GitHub Issues](https://github.com/ClermontDigital/LumaFlow/issues)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest -q
```

## Roadmap

- **Lovelace card** for at-a-glance control
- **Per-light ranges**, so a bedside lamp can be dimmer than the kitchen
- **Scene integration**
- **Presence and activity triggers**
- **Time-limited overrides**

## Changelog

### Version 1.0.0
- **Rewritten from the ground up** to do what this README describes. Existing entries keep their
  settings.
- **Fixed: setup failed** on Home Assistant 2026.1 and newer (`ATTR_COLOR_TEMP` was removed), and
  the light platform crashed during setup on older versions. ([#1](https://github.com/ClermontDigital/LumaFlow/issues/1), [#2](https://github.com/ClermontDigital/LumaFlow/issues/2))
- **Fixed: lights went to full brightness and daylight after midnight.** The night now stays at
  the night values until sunrise.
- **Fixed: the wrong day's sun times** were used for most of the morning outside UTC.
- **New: a one-hour sunrise ramp** from the night values to the day values.
- **The services work.** Enable, disable, restore and override really control the lights now.
- **Override detection** compares each light with what LumaFlow last set it to, so the bulb
  reporting back and rounding don't count as manual changes.
- **The options cover every setting**, including the lights, brightness and colour ranges.
- Light groups are expanded to their members, and each light is kept within its own colour
  temperature range.
- The wrapper light entity and per-light switches from 0.2–0.3 are removed automatically.
- No extra Python packages to install.
- Automated tests, plus hassfest and HACS validation in CI.

### Version 0.1.3 – 0.3.0
- The first releases. They didn't work reliably and are replaced by 1.0.0.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- **The Home Assistant community**, for the platform and its developer tools
- **Everyone who reported issues**, especially the two tracebacks that pinned down why setup failed
