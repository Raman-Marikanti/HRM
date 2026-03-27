from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL


Base = declarative_base()


engine = create_engine(DATABASE_URL, future=True, echo=False)


SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

