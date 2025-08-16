# models/notifications.py - Pydantic models for notifications
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class DeviceType(str, Enum):
    ANDROID = "android"
    IOS = "ios" 
    WEB = "web"

class RegisterDeviceRequest(BaseModel):
    fcm_token: str
    device_type: DeviceType
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    browser_info: Optional[str] = None
    
    @validator('fcm_token')
    def validate_fcm_token(cls, v):
        if len(v) < 100:
            raise ValueError('FCM token appears to be invalid (too short)')
        return v

class DeviceInfo(BaseModel):
    id: int
    device_type: DeviceType
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_seen: datetime

class NotificationData(BaseModel):
    title: str
    message: str
    type: str
    data: Optional[Dict[str, Any]] = None

class TestNotificationRequest(BaseModel):
    title: Optional[str] = "Test Notification"
    message: Optional[str] = "This is a test notification from your barbershop app!"
    device_types: Optional[List[DeviceType]] = None  # If None, send to all devices

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    is_read: bool
    related_booking_id: Optional[int]
    data: Optional[Dict[str, Any]]
    created_at: datetime
    push_success_count: int
    push_failure_count: int

class NotificationStats(BaseModel):
    total_notifications: int
    unread_count: int
    recent_count: int  # Last 24 hours
    push_enabled_devices: int
    active_devices: int