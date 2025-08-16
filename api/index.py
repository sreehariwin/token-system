# api/index.py - Updated with new device and notification routes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path adjustment
try:
    from config import Base, engine, IS_PRODUCTION
    import tables.users, tables.slots, tables.bookings, tables.user_sessions, tables.notifications, tables.user_devices
    from routes import users, bookings, slots, shops, notifications, devices
    
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
    version="2.0.0",
    description="A comprehensive API for barbershop booking management with multi-device notifications",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
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
    app.include_router(shops.router, tags=["Shops"])
    app.include_router(notifications.router, tags=["Notifications"])
    app.include_router(devices.router, tags=["Device Management"])

@app.get("/", tags=["Root"])
def read_root():
    """
    Welcome endpoint that provides basic API information
    """
    return {
        "message": "Barbershop Booking API", 
        "version": "2.0.0",
        "status": "running",
        "database_connected": DATABASE_CONNECTED,
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False,
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        },
        "features": [
            "User Authentication with Session Management",
            "Multi-Device Push Notifications (Android/iOS/Web)",
            "Slot Management with Time-based Restrictions",
            "Advanced Booking System with Reviews",
            "Shop Listing and Discovery",
            "Real-time Availability Tracking",
            "Device Management for Multiple Logins",
            "Comprehensive Notification System"
        ],
        "new_in_v2": [
            "Multi-device FCM token management",
            "Separate device registration per platform",
            "Enhanced notification system",
            "Device-specific notification targeting",
            "Improved notification tracking and statistics"
        ]
    }

@app.get("/health", tags=["Health"])
def health():
    """
    Health check endpoint
    """
    return {
        "status": "healthy", 
        "database": "connected" if DATABASE_CONNECTED else "disconnected",
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False,
        "version": "2.0.0"
    }

@app.get("/db-status", tags=["Health"])
def db_status():
    """
    Database connection status
    """
    if DATABASE_CONNECTED:
        return {"database": "connected", "production": IS_PRODUCTION, "version": "2.0.0"}
    else:
        return {"database": "failed", "error": "Database initialization failed"}