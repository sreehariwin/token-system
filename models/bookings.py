from pydantic import BaseModel
from datetime import datetime

class BookingRequest(BaseModel):
    slot_id: int

class BookingResponse(BaseModel):
    booking_id: int
    slot_id: int
    status: str
    booked_at: datetime

class UpdateBookingStatusRequest(BaseModel):
    booking_id: int
    new_status: str
