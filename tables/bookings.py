from sqlalchemy import Column, Integer, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from config import Base
import datetime

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    slot_id = Column(Integer, ForeignKey("slots.id"))
    status = Column(String, default="pending")
    booked_at = Column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Users", foreign_keys=[customer_id])