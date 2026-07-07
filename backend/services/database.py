from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from models.db import Base

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
