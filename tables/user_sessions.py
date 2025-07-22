# tables/user_sessions.py - New table for session management
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from config import Base
import datetime

class UserSession(Base):
    __tablename__ = 'user_sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_token = Column(String(255), unique=True, nullable=False)
    device_info = Column(String(500))  # Store device/browser info
    ip_address = Column(String(45))    # Store IP address (IPv6 compatible)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationship to user
    user = relationship("Users", back_populates="sessions")

# Update the Users table to include the relationship
# Add this to your existing tables/users.py
# In the Users class, add:
# sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")