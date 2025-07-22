# Updated api/index.py with Swagger UI enabled in production

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path adjustment
try:
    from config import Base, engine, IS_PRODUCTION
    import tables.users, tables.slots, tables.bookings, tables.user_sessions
    from routes import users, bookings, slots
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    DATABASE_CONNECTED = True
    print("✅ Database and tables initialized successfully")
except Exception as e:
    DATABASE_CONNECTED = False
    print(f"❌ Database initialization failed: {e}")

# Enable Swagger UI in production by setting docs_url and redoc_url explicitly
app = FastAPI(
    title="Barbershop Booking API",
    version="1.0.0",
    description="A comprehensive API for barbershop booking management",
    docs_url="/docs",  # Swagger UI will be available at /docs
    redoc_url="/redoc",  # ReDoc will be available at /redoc
    openapi_url="/openapi.json"  # OpenAPI schema
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers if database is connected
if DATABASE_CONNECTED:
    app.include_router(users.router, tags=["Authentication"])
    app.include_router(bookings.router, tags=["Bookings"])
    app.include_router(slots.router, tags=["Slots"])

@app.get("/", tags=["Root"])
def read_root():
    """
    Welcome endpoint that provides basic API information
    """
    return {
        "message": "Barbershop Booking API", 
        "status": "running",
        "database_connected": DATABASE_CONNECTED,
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        }
    }

@app.get("/health", tags=["Health"])
def health():
    """
    Health check endpoint
    """
    return {
        "status": "healthy", 
        "database": "connected" if DATABASE_CONNECTED else "disconnected",
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False
    }

@app.get("/db-status", tags=["Health"])
def db_status():
    """
    Database connection status
    """
    if DATABASE_CONNECTED:
        return {"database": "connected", "production": IS_PRODUCTION}
    else:
        return {"database": "failed", "error": "Database initialization failed"}