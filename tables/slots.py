from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from config import Base
import datetime

class Slot(Base):
    __tablename__ = 'slots'

    id = Column(Integer, primary_key=True)
    barber_id = Column(Integer, ForeignKey("users.id"))
    slot_time = Column(DateTime)
    is_booked = Column(Boolean, default=False)
    booked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
