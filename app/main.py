from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Fix, Sighting
from app.path_loss import distance_meters
from app.schemas import FixIn, SightingIn

app = FastAPI(title="TrackerApp Positioning API")


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
