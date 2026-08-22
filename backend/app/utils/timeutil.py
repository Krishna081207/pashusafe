"""Time helpers. Convention: everything is stored/compared in UTC; withdrawal
periods are counted as calendar days in IST (Indian farms), and an animal
"clears" at the end of the last withdrawal day (23:59:59 IST).

SQLite returns naive datetimes -- ALWAYS run values through ensure_aware()
before comparing or doing arithmetic.
"""

import math
import zoneinfo
from datetime import date, datetime, time, timedelta, timezone

IST = zoneinfo.ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def to_utc(dt: datetime) -> datetime:
    return ensure_aware(dt).astimezone(UTC)


def as_ist(dt: datetime) -> datetime:
    return to_utc(dt).astimezone(IST)


def ist_date(dt: datetime) -> date:
    return as_ist(dt).date()


def parse_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return to_utc(value)
    return to_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def withdrawal_clears_at(last_dose_at: datetime, wp_days: float | None) -> datetime:
    """End of the Nth full IST calendar day after the last dose.

    WP is rounded UP to the next whole day (safe side). A dose given today with
    a 3-day withdrawal clears at 23:59:59 IST on day+3.
    """
    days = math.ceil(wp_days) if wp_days and wp_days > 0 else 0
    local = as_ist(last_dose_at)
    clear_day = local.date() + timedelta(days=days)
    end_of_day = datetime.combine(clear_day, time(23, 59, 59), tzinfo=IST)
    return end_of_day.astimezone(UTC)


def countdown(delta: timedelta) -> str:
    """Human '2d 14h' / '5h 30m' / 'cleared' style string."""
    total_minutes = int(max(delta, timedelta(0)).total_seconds() // 60)
    days, rem = divmod(total_minutes, 1440)
    hours, minutes = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def ist_str(dt: datetime) -> str:
    return as_ist(dt).strftime("%d %b %Y, %I:%M %p IST")


def days_ago(days: int) -> datetime:
    return utcnow() - timedelta(days=days)
