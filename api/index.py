from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Barbershop Booking API", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FastAPI with CORS working!"}

@app.get("/health")
def health():
    return {"status": "healthy", "step": "basic_structure"}

# Try to add database connection
try:
    from config import Base, engine, IS_PRODUCTION
    
    # Test database connection
    if IS_PRODUCTION:
        with engine.connect() as conn:
            print("✅ Production database connection successful")
    
    @app.get("/db-status")
    def db_status():
        return {"database": "connected", "production": IS_PRODUCTION}
        
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    
    @app.get("/db-status")
    def db_status():
        return {"database": "failed", "error": str(e)}