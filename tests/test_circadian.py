"""The curve itself, with hand-made sun times (Brisbane-ish: sunrise 05:30, sunset 18:00)."""
from datetime import datetime, timedelta, timezone

from custom_components.lumaflow import circadian as c

TZ = timezone(timedelta(hours=10))
S = c.Settings(sunset_offset=0, min_brightness=1, max_brightness=100, min_kelvin=2700, max_kelvin=6500)


def day(d: int) -> c.SunDay:
    return c.SunDay(datetime(2026, 10, d, 5, 30, tzinfo=TZ), datetime(2026, 10, d, 18, 0, tzinfo=TZ))


def at(d: int, h: int, m: int = 0, settings: c.Settings = S) -> c.Target:
    return c.target(datetime(2026, 10, d, h, m, tzinfo=TZ), day(d - 1), day(d), day(d + 1), settings)


def test_day_is_bright_and_cool():
    t = at(10, 12)
    assert (t.phase, t.brightness, t.kelvin) == ("day", 100, 6500)
    assert t.next_phase == "sunset" and t.next_change == datetime(2026, 10, 10, 18, 0, tzinfo=TZ)


def test_wind_down_after_sunset():
    assert at(10, 18, 30).phase == "sunset"
    t = at(10, 20)                       # two of the four hours
    assert t.phase == "evening" and t.kelvin == 4600 and t.brightness == 50
    t = at(10, 22, 30)
    assert t.phase == "night" and (t.brightness, t.kelvin) == (1, 2700)


def test_after_midnight_stays_night():
    """0.x put lights on full daylight after midnight, because it compared with *today's* sunset."""
    t = at(11, 2)
    assert (t.phase, t.brightness, t.kelvin) == ("night", 1, 2700)
    assert t.next_phase == "sunrise" and t.next_change == datetime(2026, 10, 11, 5, 30, tzinfo=TZ)


def test_morning_ramps_up_over_an_hour():
    assert at(11, 5, 30).brightness == 1
    t = at(11, 6, 0)
    assert t.phase == "sunrise" and t.brightness == 50 and t.kelvin == 4600
    assert at(11, 6, 31).phase == "day"


def test_late_sunset_wind_down_crosses_midnight():
    """Far north in summer, sunset at 22:00 means the wind-down is still going at 01:00."""
    late = lambda d: c.SunDay(datetime(2026, 6, d, 4, 0, tzinfo=TZ), datetime(2026, 6, d, 22, 0, tzinfo=TZ))  # noqa: E731
    t = c.target(datetime(2026, 6, 11, 0, 0, tzinfo=TZ), late(10), late(11), late(12), S)
    assert t.phase == "evening" and t.brightness == 50
    assert t.next_phase == "night" and t.next_change == datetime(2026, 6, 11, 2, 0, tzinfo=TZ)


def test_sunset_offset():
    early = c.Settings(sunset_offset=-60, min_brightness=1, max_brightness=100, min_kelvin=2700, max_kelvin=6500)
    assert at(10, 17, 30, early).phase == "sunset"
    assert at(10, 17, 30).phase == "day"


def test_polar_day_and_night():
    up = c.SunDay(None, None, sun_up_at_noon=True)
    down = c.SunDay(None, None, sun_up_at_noon=False)
    now = datetime(2026, 6, 21, 12, tzinfo=TZ)
    assert c.target(now, up, up, up, S).phase == "day"
    assert c.target(now, down, down, down, S).phase == "night"
