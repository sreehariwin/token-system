# tables/users.py - Updated with device relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from config import Base
import datetime

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    email = Column(String)
    phone_number = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    is_barber = Column(Boolean, default=False)
    shop_name = Column(String, nullable=True)
    shop_address = Column(String, nullable=True)
    shop_image_url = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    create_date = Column(DateTime, default=datetime.datetime.utcnow)
    update_date = Column(DateTime)
    shop_status = Column(Boolean, default=True, nullable=True)  # True = open, False = closed 

    # Notification settings - Remove fcm_token as it's now in user_devices table
    notifications_enabled = Column(Boolean, default=True)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    barber_slots = relationship("Slot", foreign_keys="Slot.barber_id", back_populates="barber")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    