import os
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

class Base(DeclarativeBase):
    pass

def database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://erp:local_dev_only_change_me@localhost:5433/erp")

engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
