import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Check if we're in production (Vercel sets this automatically)
IS_PRODUCTION = os.getenv("VERCEL") is not None

if IS_PRODUCTION:
    # Production: Use Render database
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is required in production")
    
    SECRET_KEY = os.getenv("SECRET_KEY") 
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY is required in production")
        
    print("🚀 Running in PRODUCTION mode")
else:
    # Local: Use your existing local database
    DATABASE_URL = "postgresql://postgres:root@localhost:5432/test_api"
    SECRET_KEY = "double_dog123"
    print("💻 Running in LOCAL development mode")

# Handle Render's postgres:// URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create database engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()