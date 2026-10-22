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


class FixOut(BaseModel):
    # Read-side shape for the web map (GET /fixes/recent). camelCase to match
    # the rest of the API (and the frontend's Fix type) rather than the ORM's
    # snake_case columns, which are mapped over in the endpoint.
    id: int
    observerID: str
    x: float
    y: float
    uncertaintyMeters: float
    recordedAt: datetime
    receivedAt: datetime
