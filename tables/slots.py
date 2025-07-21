# tables/slots.py - Updated with start_time, end_time, and date
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Time, Date
from config import Base
import datetime

class Slot(Base):
    __tablename__ = 'slots'

    id = Column(Integer, primary_key=True)
    barber_id = Column(Integer, ForeignKey("users.id"))
    
    # Enhanced time management
    slot_date = Column(Date)  # Date of the appointment
    start_time = Column(Time)  # Start time
    end_time = Column(Time)    # End time
    
    # Keep the original slot_time for backward compatibility (optional)
    slot_time = Column(DateTime, nullable=True)  # Can be removed after migration
    
    is_booked = Column(Boolean, default=False)
    booked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)