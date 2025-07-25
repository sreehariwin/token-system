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
    license_number = Column(String, nullable=True)  # New field
    create_date = Column(DateTime, default=datetime.datetime.utcnow)
    update_date = Column(DateTime)
    
    # Add the missing relationship
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")