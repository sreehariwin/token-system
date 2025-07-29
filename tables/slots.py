# tables/slots.py - Updated with start_time, end_time, date, and barber relationship
from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Time, Date
from sqlalchemy.orm import relationship
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
    
    # Add the missing relationship to barber
    barber = relationship("Users", foreign_keys=[barber_id], back_populates="barber_slots")
    booked_by_user = relationship("Users", foreign_keys=[booked_by])