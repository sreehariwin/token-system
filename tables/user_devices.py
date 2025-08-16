# tables/user_devices.py - New table for managing multiple devices per user
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from config import Base
import datetime
import enum

class DeviceTypeEnum(enum.Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

class UserDevice(Base):
    __tablename__ = 'user_devices'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    device_type = Column(Enum(DeviceTypeEnum), nullable=False)
    fcm_token = Column(String(500), nullable=False)  # FCM token for this device
    device_id = Column(String(255), nullable=True)   # Unique device identifier
    device_name = Column(String(255), nullable=True) # User-friendly device name
    browser_info = Column(String(500), nullable=True) # Browser info for web devices
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship
    user = relationship("Users", back_populates="devices")




# Update tables/users.py - Add device relationship
# Add this line to the Users class in tables/users.py:
# devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")