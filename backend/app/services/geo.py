"""Small flat-earth geo helpers -- plenty accurate at farm scale (< a few km)."""

import math

EARTH_M_PER_DEG_LAT = 111_320.0


def meters_per_deg_lng(lat: float) -> float:
    return EARTH_M_PER_DEG_LAT * math.cos(math.radians(lat))


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres (rounded to 1 dp)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def offset_latlng(center_lat: float, center_lng: float, north_m: float, east_m: float) -> tuple[float, float]:
    """Point `north_m` up / `east_m` right of the centre."""
    return (
        round(center_lat + north_m / EARTH_M_PER_DEG_LAT, 6),
        round(center_lng + east_m / meters_per_deg_lng(center_lat), 6),
    )
