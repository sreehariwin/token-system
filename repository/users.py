# repository/users.py - Updated with session-based authentication
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from tables.users import Users
from tables.user_sessions import UserSession
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import get_db, SECRET_KEY, ALGORITHM, SESSION_CLEANUP_HOURS, MAX_SESSIONS_PER_USER

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

class SessionRepo:
    @staticmethod
    def create_session(db: Session, user_id: int, device_info: str = None, ip_address: str = None):
        """Create a new session for user"""
        # Generate a secure session token
        session_token = secrets.token_urlsafe(64)
        
        # Clean up old sessions if user has too many
        SessionRepo.cleanup_user_sessions(db, user_id)
        
        # Create new session
        session = UserSession(
            user_id=user_id,
            session_token=session_token,
            device_info=device_info,
            ip_address=ip_address
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def get_session_by_token(db: Session, session_token: str):
        """Get active session by token"""
        return db.query(UserSession).filter(
            and_(
                UserSession.session_token == session_token,
                UserSession.is_active == True
            )
        ).first()

    @staticmethod
    def update_session_access(db: Session, session: UserSession):
        """Update last accessed time for session"""
        session.last_accessed = datetime.utcnow()
        db.commit()

    @staticmethod
    def invalidate_session(db: Session, session_token: str):
        """Invalidate a session (logout)"""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()
        
        if session:
            session.is_active = False
            db.commit()
            return True
        return False

    @staticmethod
    def invalidate_all_user_sessions(db: Session, user_id: int):
        """Invalidate all sessions for a user (logout from all devices)"""
        db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).update({"is_active": False})
        db.commit()

    @staticmethod
    def cleanup_user_sessions(db: Session, user_id: int):
        """Keep only the most recent MAX_SESSIONS_PER_USER sessions"""
        active_sessions = db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).order_by(UserSession.last_accessed.desc()).all()
        
        if len(active_sessions) >= MAX_SESSIONS_PER_USER:
            # Deactivate oldest sessions
            sessions_to_deactivate = active_sessions[MAX_SESSIONS_PER_USER-1:]
            for session in sessions_to_deactivate:
                session.is_active = False
            db.commit()

    @staticmethod
    def cleanup_old_sessions(db: Session):
        """Clean up very old inactive sessions"""
        cutoff_date = datetime.utcnow() - timedelta(hours=SESSION_CLEANUP_HOURS)
        db.query(UserSession).filter(
            and_(
                UserSession.last_accessed < cutoff_date,
                UserSession.is_active == False
            )
        ).delete()
        db.commit()

class JWTRepo:
    @staticmethod
    def generate_session_token(session_token: str):
        """Generate JWT token that contains session reference"""
        # Create a payload with session token reference
        payload = {
            "session": session_token,
            "type": "session"
        }
        
        # Generate JWT without expiration
        encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_session_token(token: str):
        """Verify JWT token and extract session token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            session_token = payload.get("session")
            token_type = payload.get("type")
            
            if session_token is None or token_type != "session":
                raise JWTError("Invalid token format")
                
            return session_token
        except JWTError:
            return None

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user from session token"""
    token = credentials.credentials
    session_token = JWTRepo.verify_session_token(token)
    
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get session from database
    session = SessionRepo.get_session_by_token(db, session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update session access time
    SessionRepo.update_session_access(db, session)
    
    # Get user
    user = db.query(Users).filter(Users.id == session.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current session object"""
    token = credentials.credentials
    session_token = JWTRepo.verify_session_token(token)
    
    if session_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    session = SessionRepo.get_session_by_token(db, session_token)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return session