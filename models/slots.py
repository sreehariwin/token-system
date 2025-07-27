# models/slots.py - Updated with enhanced support for multiple slots
from pydantic import BaseModel, validator
from datetime import datetime, date, time
from typing import Optional, List

class SlotCreate(BaseModel):
    slot_date: date  # Date for the slot (YYYY-MM-DD)
    start_time: time  # Start time (HH:MM:SS)
    end_time: time    # End time (HH:MM:SS)
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v
    
    @validator('slot_date')
    def validate_slot_date(cls, v):
        if v < date.today():
            raise ValueError('Slot date cannot be in the past')
        return v

class SlotCreateMultiple(BaseModel):
    """For creating multiple identical slots"""
    slot_date: date
    start_time: time
    end_time: time
    count: int  # Number of identical slots to create
    
    @validator('count')
    def validate_count(cls, v):
        if v < 1 or v > 50:
            raise ValueError('Count must be between 1 and 50')
        return v
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v
    
    @validator('slot_date')
    def validate_slot_date(cls, v):
        if v < date.today():
            raise ValueError('Slot date cannot be in the past')
        return v

class SlotCreateBulk(BaseModel):
    """For creating multiple slots at once with different times"""
    slot_date: date
    time_slots: list[dict]  # [{"start_time": "09:00", "end_time": "10:00", "count": 2}, ...]
    
    @validator('time_slots')
    def validate_time_slots(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one time slot is required')
        
        for slot in v:
            if 'start_time' not in slot or 'end_time' not in slot:
                raise ValueError('Each time slot must have start_time and end_time')
            
            # Validate count if provided
            count = slot.get('count', 1)
            if not isinstance(count, int) or count < 1 or count > 10:
                raise ValueError('Count for each time slot must be between 1 and 10')
            
            # Convert string times to time objects for validation
            try:
                start = time.fromisoformat(slot['start_time'])
                end = time.fromisoformat(slot['end_time'])
                if end <= start:
                    raise ValueError(f'End time {slot["end_time"]} must be after start time {slot["start_time"]}')
            except ValueError as e:
                if 'after start time' in str(e):
                    raise e
                raise ValueError(f'Invalid time format: {e}')
        
        return v

class SlotResponse(BaseModel):
    id: int
    slot_date: date
    start_time: time
    end_time: time
    is_booked: bool
    booked_by: Optional[int] = None
    barber_id: int
    
    # Computed field for display purposes
    @property
    def duration_minutes(self) -> int:
        """Calculate slot duration in minutes"""
        start_dt = datetime.combine(date.today(), self.start_time)
        end_dt = datetime.combine(date.today(), self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)
    
    class Config:
        from_attributes = True

class SlotFilter(BaseModel):
    """For filtering slots by date range"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    barber_id: Optional[int] = None
    available_only: bool = True

class SlotTimeCount(BaseModel):
    """Response model for slot counts by time"""
    start_time: time
    end_time: time
    total_slots: int
    available_slots: int
    booked_slots: int

class SlotCountResponse(BaseModel):
    """Response model for slot count endpoint"""
    date: date
    barber_id: Optional[int]
    time_slots: List[SlotTimeCount]

class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations"""
    slot_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    unbooked_only: bool = True

class TemplateGenerateRequest(BaseModel):
    """Request model for template generation"""
    start_date: date
    daily_slots: str = "09:00-10:00,10:00-11:00,11:00-12:00,14:00-15:00,15:00-16:00,16:00-17:00"
    slots_per_time: int = 1
    exclude_weekends: bool = True
    
    @validator('slots_per_time')
    def validate_slots_per_time(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Slots per time must be between 1 and 10')
        return v