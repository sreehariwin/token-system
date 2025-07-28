# tables/bookings.py - Enhanced booking table with ratings
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from config import Base
import datetime

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    slot_id = Column(Integer, ForeignKey("slots.id"))
    status = Column(String, default="pending")  # pending, confirmed, in_progress, completed, cancelled, no_show
    special_requests = Column(Text, nullable=True)  # Customer's special requests
    cancellation_reason = Column(String(200), nullable=True)  # Reason for cancellation
    
    # Rating and review fields
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    review_text = Column(Text, nullable=True)  # Customer's review
    
    # Timestamps
    booked_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    customer = relationship("Users", foreign_keys=[customer_id])
    slot = relationship("Slot", backref="booking")