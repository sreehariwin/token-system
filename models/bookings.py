# models/bookings.py - Enhanced booking models
from pydantic import BaseModel, validator
from datetime import datetime, date, time
from typing import Optional

class BookingRequest(BaseModel):
    slot_id: int
    special_requests: Optional[str] = None
    
    @validator('special_requests')
    def validate_special_requests(cls, v):
        if v and len(v) > 500:
            raise ValueError('Special requests cannot exceed 500 characters')
        return v

class BookingResponse(BaseModel):
    booking_id: int
    slot_id: int
    status: str
    booked_at: datetime
    slot_date: date
    start_time: time
    end_time: time
    barber_name: str
    shop_name: str
    can_modify: bool

class BookingDetailsResponse(BaseModel):
    booking_id: int
    slot_id: int
    status: str
    booked_at: datetime
    slot_date: date
    start_time: time
    end_time: time
    barber_id: int
    barber_name: str
    shop_name: str
    shop_address: Optional[str] = None
    shop_image_url: Optional[str] = None
    barber_phone: str
    special_requests: Optional[str] = None
    can_modify: bool
    is_past: bool

class BookingUpdateRequest(BaseModel):
    new_slot_id: Optional[int] = None
    special_requests: Optional[str] = None
    
    @validator('special_requests')
    def validate_special_requests(cls, v):
        if v and len(v) > 500:
            raise ValueError('Special requests cannot exceed 500 characters')
        return v

class CancelBookingRequest(BaseModel):
    reason: Optional[str] = None
    
    @validator('reason')
    def validate_reason(cls, v):
        if v and len(v) > 200:
            raise ValueError('Cancellation reason cannot exceed 200 characters')
        return v

class RatingRequest(BaseModel):
    rating: int
    review_text: Optional[str] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
    
    @validator('review_text')
    def validate_review_text(cls, v):
        if v and len(v) > 1000:
            raise ValueError('Review text cannot exceed 1000 characters')
        return v

class UpdateBookingStatusRequest(BaseModel):
    booking_id: int
    new_status: str
    
    @validator('new_status')
    def validate_status(cls, v):
        valid_statuses = ["pending", "confirmed", "in_progress", "completed", "cancelled", "no_show"]
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v