import math

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Ikki nuqta orasidagi masofa (haversine), metrda.

    MySQL'dagi ST_Distance_Sphere bilan bir xil sferik model; Python'da hisoblash
    testlarni bazadan mustaqil qiladi.
    """
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * EARTH_RADIUS_M * math.asin(math.sqrt(h)))


def valid_coords(lat: float, lng: float) -> bool:
    return -90 <= lat <= 90 and -180 <= lng <= 180
