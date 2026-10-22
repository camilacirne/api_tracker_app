from datetime import datetime

from pydantic import BaseModel


class SightingIn(BaseModel):
    observerID: str
    anchorID: str
    rssi: int
    # Optional and ignored server-side — kept so existing clients (the iOS app) that already
    # compute and send this don't need to change. distance_meters is always recomputed from
    # rssi in path_loss.py instead, so there's one canonical formula instead of one per client
    # (Swift today, Kotlin and ESP32 firmware eventually).
    distanceMeters: float | None = None
    seenAt: datetime


class FixIn(BaseModel):
    observerID: str
    x: float
    y: float
    uncertaintyMeters: float
    recordedAt: datetime
