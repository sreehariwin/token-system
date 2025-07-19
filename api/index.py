from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import after path adjustment
try:
    from config import Base, engine, IS_PRODUCTION
    import tables.users, tables.slots, tables.bookings
    from routes import users, bookings, slots
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    DATABASE_CONNECTED = True
    print("✅ Database and tables initialized successfully")
except Exception as e:
    DATABASE_CONNECTED = False
    print(f"❌ Database initialization failed: {e}")

app = FastAPI(title="Barbershop Booking API", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers if database is connected
if DATABASE_CONNECTED:
    app.include_router(users.router)
    app.include_router(bookings.router)
    app.include_router(slots.router)

@app.get("/")
def read_root():
    return {
        "message": "Barbershop Booking API", 
        "status": "running",
        "database_connected": DATABASE_CONNECTED,
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False
    }

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "database": "connected" if DATABASE_CONNECTED else "disconnected",
        "production": IS_PRODUCTION if DATABASE_CONNECTED else False
    }

@app.get("/db-status")
def db_status():
    if DATABASE_CONNECTED:
        return {"database": "connected", "production": IS_PRODUCTION}
    else:
        return {"database": "failed", "error": "Database initialization failed"}