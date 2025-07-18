from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:root@localhost:5432/test_api"

engine = create_engine(DATABASE_URL)
SesionLocal = sessionmaker(autocommit=False, autoflush=False,bind=engine)
Base = declarative_base()

def get_db():
    db = SesionLocal()
    try:
        yield db
    finally: db.close()

SECRET_KEY="double_dog123"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30