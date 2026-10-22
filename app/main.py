import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Fix, Sighting
from app.path_loss import distance_meters
from app.schemas import FixIn, FixOut, SightingIn

app = FastAPI(title="TrackerApp Positioning API")

# The web map is a browser app on a different origin, so it needs CORS to read
# /fixes/recent. CORS_ORIGINS is a comma-separated allowlist; default "*" is
# fine for local dev but should be set to the real frontend origin in prod.
_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sightings", status_code=201)
def create_sightings(reports: list[SightingIn], db: Session = Depends(get_db)) -> dict[str, int]:
    received_at = datetime.now(timezone.utc)
    rows = [
        Sighting(
            observer_id=report.observerID,
            anchor_id=report.anchorID,
            rssi=report.rssi,
            distance_meters=distance_meters(report.rssi),
            seen_at=report.seenAt,
            received_at=received_at,
        )
        for report in reports
    ]
    db.add_all(rows)
    db.commit()
    return {"inserted": len(rows)}


@app.get("/fixes/recent")
def recent_fixes(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[FixOut]:
    """Most recent position fixes, newest first — the read side the web map polls.

    Returns up to `limit` rows ordered by recorded time. The map groups these by
    observerID into per-device tracks (newest = current dot, rest = trail).
    """
    rows = (
        db.execute(select(Fix).order_by(Fix.recorded_at.desc()).limit(limit))
        .scalars()
        .all()
    )
    return [
        FixOut(
            id=row.id,
            observerID=row.observer_id,
            x=row.x,
            y=row.y,
            uncertaintyMeters=row.uncertainty_meters,
            recordedAt=row.recorded_at,
            receivedAt=row.received_at,
        )
        for row in rows
    ]


@app.post("/fixes", status_code=201)
def create_fix(report: FixIn, db: Session = Depends(get_db)) -> dict[str, int]:
    row = Fix(
        observer_id=report.observerID,
        x=report.x,
        y=report.y,
        uncertainty_meters=report.uncertaintyMeters,
        recorded_at=report.recordedAt,
        received_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return {"inserted": 1}
