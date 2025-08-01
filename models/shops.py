# models/shops.py - Models for shop listing API
from pydantic import BaseModel, validator
from datetime import date, time
from typing import Optional, List, Dict, Any

class ShopListResponse(BaseModel):
    barber_id: int
    shop_name: str
    shop_address: Optional[str] = None
    shop_image_url: Optional[str] = None
    barber_name: str
    phone_number: str
    license_number: Optional[str] = None
    avg_rating: float = 0.0
    total_reviews: int = 0
    available_slots_count: Optional[int] = None
    next_available_slot: Optional[date] = None
    next_available_time: Optional[time] = None
    shop_status: bool = True 

class ReviewResponse(BaseModel):
    customer_name: str
    rating: int
    review_text: Optional[str] = None
    date: Optional[date] = None # type: ignore

class AvailableSlotResponse(BaseModel):
    slot_id: int
    slot_date: date
    start_time: time
    end_time: time

class ShopDetailsResponse(BaseModel):
    barber_id: int
    shop_name: str
    shop_address: Optional[str] = None
    shop_image_url: Optional[str] = None
    barber_name: str
    phone_number: str
    email: str
    license_number: Optional[str] = None
    avg_rating: float = 0.0
    total_reviews: int = 0
    recent_reviews: List[Dict[str, Any]] = []
    available_slots: List[Dict[str, Any]] = []
    business_hours: Dict[str, str] = {}
    member_since: Optional[date] = None
    shop_status: bool = True 

class ShopSearchRequest(BaseModel):
    query: Optional[str] = None
    city: Optional[str] = None
    min_rating: Optional[float] = None
    has_available_slots: bool = False
    sort_by: str = "rating"
    
    @validator('min_rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        valid_sorts = ['rating', 'name', 'distance', 'availability']
        if v not in valid_sorts:
            raise ValueError(f'sort_by must be one of: {", ".join(valid_sorts)}')
        return v

class NearbyShopRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 10.0
    limit: int = 20
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v
    
    @validator('radius_km')
    def validate_radius(cls, v):
        if not 0 < v <= 50:
            raise ValueError('Radius must be between 0 and 50 km')
        return v