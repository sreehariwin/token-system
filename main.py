from fastapi import FastAPI
from config import Base, engine
import tables.users, tables.slots, tables.bookings, tables.user_sessions
from routes import users, bookings, slots, shops

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(users.router)
app.include_router(bookings.router)
app.include_router(slots.router)
app.include_router(shops.router)