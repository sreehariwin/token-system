# tables/notifications.py - Updated notification table
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from config import Base
import datetime

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  # booking_received, booking_confirmed, etc.
    is_read = Column(Boolean, default=False)
    related_booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=True)
    data = Column(JSON, nullable=True)  # Additional data for the notification
    sent_to_devices = Column(JSON, nullable=True)  # Track which devices received push notification
    push_success_count = Column(Integer, default=0)  # Number of devices that received push
    push_failure_count = Column(Integer, default=0)  # Number of devices that failed to receive push
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    user = relationship("Users", back_populates="notifications")
    booking = relationship("Booking")
