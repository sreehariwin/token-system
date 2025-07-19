# models/slots.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SlotCreate(BaseModel):
    slot_time: datetime

class SlotResponse(BaseModel):
    id: int
    slot_time: datetime
    is_booked: bool
    booked_by: Optional[int] = None

    class Config:
        from_attributes = True  # Updated for Pydantic v2