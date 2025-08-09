# config.py - Updated with session management settings
import os
import cloudinary
import cloudinary.uploader
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Check if we're in production (Vercel sets this automatically)
IS_PRODUCTION = os.getenv("VERCEL") is not None or os.getenv("VERCEL_ENV") is not None

if IS_PRODUCTION:
    # Production: Use environment variables
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is required in production")
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required in production")
    
    # Cloudinary configuration for production
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        print("⚠️ Warning: Cloudinary credentials not found. Image upload will be disabled.")
        CLOUDINARY_ENABLED = False
    else:
        CLOUDINARY_ENABLED = True
        
    FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    print(f"🚀 Running in PRODUCTION mode")
    print(f"📊 Database URL: {DATABASE_URL[:50]}...")  # Only show first 50 chars for security
else:
    # Local: Use your existing local database
    DATABASE_URL = "postgresql://postgres:root@localhost:5432/test_api"
    SECRET_KEY = "double_dog123"
    
    # Local Cloudinary configuration (optional for local testing)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")  
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    CLOUDINARY_ENABLED = bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
    
    print("💻 Running in LOCAL development mode")

# Configure Cloudinary if enabled
if CLOUDINARY_ENABLED:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    print("☁️ Cloudinary configured successfully")
else:
    print("⚠️ Cloudinary disabled - images will not be uploaded")

# Handle different PostgreSQL URL formats
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create database engine with better error handling
try:
    engine = create_engine(
        DATABASE_URL, 
        pool_pre_ping=True,
        pool_recycle=300,  # Recycle connections every 5 minutes
        echo=False  # Set to True for SQL debugging
    )
    
    # Test the connection
    with engine.connect() as conn:
        print("✅ Database connection successful")
        
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT settings - Updated for session-based auth
ALGORITHM = "HS256"
# Remove ACCESS_TOKEN_EXPIRE_MINUTES since tokens won't expire automatically
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Session management settings
SESSION_CLEANUP_HOURS = 24 * 30  # Clean up inactive sessions after 30 days
MAX_SESSIONS_PER_USER = 5  # Maximum concurrent sessions per user

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()