# models/users.py - Updated with session management models
from pydantic import BaseModel, validator
from typing import Optional, Any, List
from datetime import datetime

class Register(BaseModel):
    username: str
    password: str
    email: str
    phone_number: str
    first_name: str
    last_name: str
    is_barber: bool = False
    shop_name: Optional[str] = None
    shop_address: Optional[str] = None
    shop_image_url: Optional[str] = None
    license_number: Optional[str] = None

class Login(BaseModel):
    phone_number: str
    password: str

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('New password must be at least 6 characters long')
        return v
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    expires_on_logout: bool = True  # Indicate that token doesn't auto-expire

class SessionInfo(BaseModel):
    """Information about user sessions"""
    session_id: int
    device_info: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    last_accessed: datetime
    is_current: bool = False

class ActiveSessionsResponse(BaseModel):
    """Response model for active sessions"""
    total_sessions: int
    sessions: List[SessionInfo]

class LogoutRequest(BaseModel):
    """Request model for logout"""
    logout_all_devices: bool = False

class ResponseSchema(BaseModel):
    code: str
    status: str
    message: str
    result: Optional[Any] = None

# Booking models (keeping existing ones)
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