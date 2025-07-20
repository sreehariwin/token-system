# repository/users.py - Updated to use phone_number for authentication

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from tables.users import Users
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_db, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class UserRepo:
    @staticmethod
    def insert(db: Session, user: Users):
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def find_by_username(db: Session, model, username: str):
        """Keep this for backward compatibility with signup"""
        return db.query(model).filter(model.username == username).first()

    @staticmethod
    def find_by_phone_number(db: Session, model, phone_number: str):
        """New method to find user by phone number"""
        return db.query(model).filter(model.phone_number == phone_number).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str):
        """Keep this for JWT token validation"""
        return db.query(Users).filter(Users.username == username).first()

    @staticmethod
    def get_user_by_phone_number(db: Session, phone_number: str):
        """New method to get user by phone number for login"""
        return db.query(Users).filter(Users.phone_number == phone_number).first()

    @staticmethod
    def update_user_password(db: Session, user: Users, new_password_hash: str):
        """Update user's password"""
        user.password = new_password_hash
        user.update_date = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

class JWTRepo:
    @staticmethod
    def generate_token(data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")  # Still using username in JWT payload
            if username is None:
                raise JWTError("Token invalid - no subject")
            return username
        except JWTError:
            return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    username = JWTRepo.verify_token(token)
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = UserRepo.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user