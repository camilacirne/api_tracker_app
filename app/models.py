from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Sighting(Base):
    __tablename__ = "sightings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Not fixed at 8 chars (the length of a BeaconID) — an ESP32 station or other non-phone
    # sender identifies itself with its own, differently-shaped id.
    observer_id: Mapped[str] = mapped_column(String(64), index=True)
    anchor_id: Mapped[str] = mapped_column(String(64), index=True)
    rssi: Mapped[int] = mapped_column(Integer)
    distance_meters: Mapped[float] = mapped_column(Float)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Fix(Base):
    __tablename__ = "fixes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observer_id: Mapped[str] = mapped_column(String(64), index=True)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    uncertainty_meters: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
