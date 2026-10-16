import os
from sqlalchemy import create_engine, String, Integer, Float, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    capacity: Mapped[int] = mapped_column(Integer)
    booked: Mapped[int] = mapped_column(Integer, default=0)


class Registration(Base):
    __tablename__ = "registrations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String(160))
    key: Mapped[str] = mapped_column(String(100), unique=True)
    __table_args__ = (__import__("sqlalchemy").UniqueConstraint("event_id", "email"),)


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(8))
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON)
    timeline: Mapped[list] = mapped_column(JSON)
    notes: Mapped[str] = mapped_column(String(2000), default="")


def connect(url=None):
    url = url or os.getenv("DATABASE_URL", "sqlite:///./eventpulse.db")
    engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        if db.get(Event, 1) is None:
            db.add_all(
                [
                    Event(id=1, name="Cloud & Reliability Summit", capacity=10000),
                    Event(id=2, name="Platform Engineering Workshop", capacity=5000),
                    Event(id=3, name="Open Source Community Night", capacity=2500),
                ]
            )
    return engine, factory
