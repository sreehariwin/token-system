from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your existing route files
from routes.users import router as auth_router
from routes.slots import router as slots_router  
from routes.bookings import router as bookings_router

app = FastAPI(
    title="Barbershop Booking API", 
    version="1.0.0"
)

# Add CORS (needed for frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add your existing routes
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(slots_router, prefix="/slots", tags=["Slots"])
app.include_router(bookings_router, prefix="/bookings", tags=["Bookings"])

@app.get("/")
def home():
    return {"message": "Barbershop Booking API is running!"}

# This is required for Vercel
handler = app