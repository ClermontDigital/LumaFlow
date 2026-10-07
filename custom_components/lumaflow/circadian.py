"""The circadian curve: what brightness and colour temperature lights should have at a given moment.

Pure Python, no Home Assistant imports, so it can be tested on its own.

The day is anchored on sunrise and on "dusk", which is sunset plus the configured offset:

    sunrise ──1 h──▶ day ─────────────▶ dusk ──1 h──▶ evening ──3 h──▶ night ─────▶ next sunrise
    (ramp up)        (max, coolest)          (sunset)   (dimming)        (min, warmest)

From dusk, brightness and colour temperature fall linearly from the day values to the night
values over four hours (the first hour is the "sunset" phase, the rest "evening"). After sunrise
they rise back over one hour, so mornings brighten gently instead of jumping.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

PHASE_SUNRISE = "sunrise"
PHASE_DAY = "day"
PHASE_SUNSET = "sunset"
PHASE_EVENING = "evening"
PHASE_NIGHT = "night"
PHASES = [PHASE_SUNRISE, PHASE_DAY, PHASE_SUNSET, PHASE_EVENING, PHASE_NIGHT]

SUNRISE_RAMP = timedelta(hours=1)
SUNSET_PHASE = timedelta(hours=1)
WIND_DOWN = timedelta(hours=4)   # dusk to full night values


@dataclass(frozen=True)
class Settings:
    sunset_offset: int = 0        # minutes, -120..120
    min_brightness: int = 1       # %
    max_brightness: int = 100     # %
    min_kelvin: int = 2700        # warmest, used at night
    max_kelvin: int = 6500        # coolest, used in the day


@dataclass(frozen=True)
class SunDay:
    """One local calendar day's sun events. None when the sun doesn't rise or set (polar day/night)."""

    sunrise: datetime | None
    sunset: datetime | None
    sun_up_at_noon: bool = True   # used only when there's no sunrise or sunset


@dataclass(frozen=True)
class Target:
    phase: str
    brightness: int          # %
    kelvin: int
    progress: float          # 0 = day values, 1 = night values
    next_phase: str
    next_change: datetime | None


def _lerp(day: float, night: float, progress: float) -> float:
    return day + (night - day) * progress


def _values(settings: Settings, progress: float) -> tuple[int, int]:
    progress = min(1.0, max(0.0, progress))
    brightness = round(_lerp(settings.max_brightness, settings.min_brightness, progress))
    kelvin = round(_lerp(settings.max_kelvin, settings.min_kelvin, progress))
    return max(1, min(100, brightness)), kelvin


def _dusk(sun: SunDay, settings: Settings) -> datetime | None:
    return sun.sunset + timedelta(minutes=settings.sunset_offset) if sun.sunset else None


def _wind_down(now: datetime, dusk: datetime) -> float:
    return (now - dusk) / WIND_DOWN


def target(now: datetime, yesterday: SunDay, today: SunDay, tomorrow: SunDay, settings: Settings) -> Target:
    """Brightness and colour temperature for `now` (timezone aware, local).

    `yesterday`, `today` and `tomorrow` are the sun events for the local dates around `now`.
    Yesterday's dusk matters after midnight: with a late sunset the wind-down can still be going.
    """
    dusk_y, dusk_t, dusk_n = _dusk(yesterday, settings), _dusk(today, settings), _dusk(tomorrow, settings)
    rise_t, rise_n = today.sunrise, tomorrow.sunrise

    # Polar day or night: no sunrise or no dusk today, so stay on day or night values.
    if rise_t is None or dusk_t is None:
        if today.sun_up_at_noon:
            b, k = _values(settings, 0.0)
            return Target(PHASE_DAY, b, k, 0.0, PHASE_DAY, None)
        b, k = _values(settings, 1.0)
        return Target(PHASE_NIGHT, b, k, 1.0, PHASE_NIGHT, None)

    if rise_t <= now < dusk_t:
        # Daytime: a one-hour ramp up from wherever last night's wind-down got to, then full day.
        if now < rise_t + SUNRISE_RAMP:
            start = min(1.0, _wind_down(rise_t, dusk_y)) if dusk_y else 1.0
            ramp = (now - rise_t) / SUNRISE_RAMP
            progress = start * (1 - ramp)
            b, k = _values(settings, progress)
            return Target(PHASE_SUNRISE, b, k, progress, PHASE_DAY, rise_t + SUNRISE_RAMP)
        b, k = _values(settings, 0.0)
        return Target(PHASE_DAY, b, k, 0.0, PHASE_SUNSET, dusk_t)

    # Night side: measure the wind-down from the most recent dusk.
    if now >= dusk_t:
        dusk, next_rise, next_dusk = dusk_t, rise_n, dusk_n
    else:   # before today's sunrise
        dusk, next_rise, next_dusk = dusk_y, rise_t, dusk_t
    if dusk is None:
        b, k = _values(settings, 1.0)
        return Target(PHASE_NIGHT, b, k, 1.0, PHASE_SUNRISE, next_rise)
    progress = min(1.0, max(0.0, _wind_down(now, dusk)))
    b, k = _values(settings, progress)
    candidates = [(dusk + SUNSET_PHASE, PHASE_EVENING), (dusk + WIND_DOWN, PHASE_NIGHT), (next_rise, PHASE_SUNRISE)]
    upcoming = sorted((t, p) for t, p in candidates if t is not None and t > now)
    nxt_time, nxt_phase = upcoming[0] if upcoming else (next_dusk, PHASE_SUNSET)
    if now < dusk + SUNSET_PHASE:
        phase = PHASE_SUNSET
    elif now < dusk + WIND_DOWN:
        phase = PHASE_EVENING
    else:
        phase = PHASE_NIGHT
    return Target(phase, b, k, progress, nxt_phase, nxt_time)
