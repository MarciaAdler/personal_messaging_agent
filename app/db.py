import json
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

Base = declarative_base()

# Railway's Postgres plugin gives a "postgres://" URL; SQLAlchemy 2.x wants "postgresql://",
# and we force the pure-Python pg8000 driver to avoid needing the system libpq.so at runtime.
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class LastList(Base):
    """
    Stores the most recent numbered to-do list Clara showed the user, so that
    replies like "mark 2 done" can be resolved to the correct Notion page.
    Single-user app, so we just keep one row (id=1) and overwrite it.
    """
    __tablename__ = "last_list"
    id = Column(Integer, primary_key=True)
    items_json = Column(Text, nullable=False)  # [{"num": 1, "page_id": "...", "title": "..."}]
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def save_last_list(items):
    """items: list of dicts with keys num, page_id, title"""
    session = SessionLocal()
    try:
        row = session.get(LastList, 1)
        payload = json.dumps(items)
        if row:
            row.items_json = payload
            row.created_at = datetime.datetime.utcnow()
        else:
            row = LastList(id=1, items_json=payload)
            session.add(row)
        session.commit()
    finally:
        session.close()


def get_last_list():
    session = SessionLocal()
    try:
        row = session.get(LastList, 1)
        if not row:
            return []
        return json.loads(row.items_json)
    finally:
        session.close()


class ConsentRecord(Base):
    """Audit trail of SMS opt-in submissions from the /consent form."""
    __tablename__ = "consent_records"
    id = Column(Integer, primary_key=True)
    phone_number = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def save_consent(phone_number):
    session = SessionLocal()
    try:
        row = ConsentRecord(phone_number=phone_number)
        session.add(row)
        session.commit()
    finally:
        session.close()
