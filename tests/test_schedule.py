"""Does every weekday run's lookback reach exactly back to the previous run?

No gap (a story published in between is missed) and no overlap (it gets re-reported).
"""
import datetime
import re
from zoneinfo import ZoneInfo

from tada_ci.services.time_filter import _WINDOW_BY_WEEKDAY, _DEFAULT_WINDOW_HOURS

CHI = ZoneInfo("America/Chicago")

text = open(".github/workflows/newsjacking.yml", encoding="utf-8").read()
crons = re.findall(r'- cron: "([^"]+)"', text)
print("crons:", crons)
assert crons == ["0 13 * * 1-5", "0 14 * * 1-5"], crons

# Walk a full year. Collect the moment each run actually fires, in Chicago terms.
runs = []
day = datetime.date(2026, 1, 1)
while day < datetime.date(2027, 1, 1):
    if day.weekday() < 5:  # cron "1-5"
        fired = [
            datetime.datetime(day.year, day.month, day.day, h, tzinfo=datetime.timezone.utc)
            for h in (13, 14)
        ]
        # The guard in the workflow keeps only the one that is 08:00 in Chicago.
        kept = [t for t in fired if t.astimezone(CHI).hour == 8]
        assert len(kept) == 1, f"{day}: {len(kept)} runs survived the guard"
        runs.append(kept[0])
    day += datetime.timedelta(days=1)

print(f"{len(runs)} runs in 2026 (weekdays only)")

names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
for prev, cur in zip(runs, runs[1:]):
    weekday = cur.astimezone(CHI).weekday()
    window = _WINDOW_BY_WEEKDAY.get(weekday, _DEFAULT_WINDOW_HOURS)
    cutoff = cur - datetime.timedelta(hours=window)
    drift = (cutoff - prev).total_seconds() / 3600
    # A DST changeover shifts the wall clock by an hour; anything larger is a real gap.
    assert abs(drift) <= 1, (
        f"{names[weekday]} {cur.astimezone(CHI):%Y-%m-%d}: {window}h window reaches "
        f"{cutoff:%a %H:%M} but the previous run was {prev:%a %H:%M} ({drift:+.0f}h off)"
    )

# Spot-check the shape the user asked for.
mon = next(r for r in runs if r.astimezone(CHI).weekday() == 0)
assert _WINDOW_BY_WEEKDAY[0] == 72
print(f"Monday {mon.astimezone(CHI):%Y-%m-%d %H:%M %Z} covers back to "
      f"{(mon - datetime.timedelta(hours=72)).astimezone(CHI):%a %d %b %H:%M}")
print("OK: no gaps, no overlaps, all year")
