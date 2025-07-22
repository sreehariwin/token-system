# routes/users.py - Updated with session-based authentication
from fastapi import APIRouter, Depends, HTTPException, Request
from models.users import (
    TokenResponse, Register, Login, ResponseSchema, ChangePassword,
    ActiveSessionsResponse, LogoutRequest, SessionInfo
)
from sqlalchemy.orm import Session
from config import get_db
from passlib.context import CryptContext
from repository.users import (
    UserRepo, JWTRepo, SessionRepo, get_current_user, get_current_session
)
from tables.users import Users
from tables.user_sessions import UserSession
from utils.cloudinary_helper import upload_base64_image

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

def get_client_info(request: Request):
    """Extract client information from request"""
    user_agent = request.headers.get('user-agent', 'Unknown')
    ip_address = request.client.host if request.client else 'Unknown'
    
    # Extract browser/device info from user agent
    device_info = user_agent[:500]  # Limit to 500 chars
    
    return device_info, ip_address

@router.post('/signup')
async def signup(request: Register, req: Request, db: Session = Depends(get_db)):
    try:
        # Check if username already exists
        existing_user_by_username = UserRepo.find_by_username(db, Users, request.username)
        if existing_user_by_username:
            return ResponseSchema(
                code="400", 
                status="Error", 
                message="Username already exists"
            ).dict(exclude_none=True)

        # Check if phone number already exists
        existing_user_by_phone = UserRepo.find_by_phone_number(db, Users, request.phone_number)
        if existing_user_by_phone:
            return ResponseSchema(
                code="400", 
                status="Error", 
                message="Phone number already exists"
            ).dict(exclude_none=True)

        # Handle image upload if provided
        final_image_url = None
        if request.is_barber and request.shop_image_url:
            if request.shop_image_url.startswith('data:image') or not request.shop_image_url.startswith('http'):
                try:
                    final_image_url = upload_base64_image(
                        request.shop_image_url, 
                        folder=f"barbershop/{request.username}"
                    )
                    print(f"✅ Image uploaded to Cloudinary: {final_image_url}")
                except Exception as e:
                    print(f"⚠️ Image upload failed: {e}")
                    final_image_url = None
            else:
                final_image_url = request.shop_image_url

        # Create new user
        _user = Users(
            username=request.username,
            password=pwd_context.hash(request.password),
            email=request.email,
            phone_number=request.phone_number,
            first_name=request.first_name,
            last_name=request.last_name,
            is_barber=request.is_barber,
            shop_name=request.shop_name if request.is_barber else None,
            shop_address=request.shop_address if request.is_barber else None,
            shop_image_url=final_image_url,
            license_number=request.license_number if request.is_barber else None
        )
        
        UserRepo.insert(db, _user)
        
        # Create session for auto-login
        device_info, ip_address = get_client_info(req)
        session = SessionRepo.create_session(db, _user.id, device_info, ip_address)
        
        # Generate JWT token with session reference
        token = JWTRepo.generate_session_token(session.session_token)
        role = "barber" if _user.is_barber else "customer"
        
        # Prepare response data
        response_data = {
            "access_token": token,
            "token_type": "bearer",
            "role": role,
            "user_id": _user.id,
            "phone_number": _user.phone_number,
            "username": _user.username,
            "expires_on_logout": True
        }
        
        # Add barber-specific information if user is a barber
        if _user.is_barber:
            response_data.update({
                "shop_name": _user.shop_name,
                "shop_address": _user.shop_address,
                "shop_image_url": final_image_url,
                "license_number": _user.license_number
            })
        
        return ResponseSchema(
            code="200", 
            status="OK", 
            message="User registered and logged in successfully",
            result=response_data
        ).dict(exclude_none=True)
        
    except Exception as e:
        print(f"Signup error: {e}")
        return ResponseSchema(
            code="500", 
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.post('/login')
async def login(request: Login, req: Request, db: Session = Depends(get_db)):
    try:
        # Find user by phone number
        _user = UserRepo.find_by_phone_number(db, Users, request.phone_number)

        if not _user or not pwd_context.verify(request.password, _user.password):
            return ResponseSchema(
                code="400", 
                status="Bad Request", 
                message="Invalid phone number or password"
            ).dict(exclude_none=True)

        # Create new session
        device_info, ip_address = get_client_info(req)
        session = SessionRepo.create_session(db, _user.id, device_info, ip_address)
        
        # Generate JWT token with session reference
        token = JWTRepo.generate_session_token(session.session_token)
        role = "barber" if _user.is_barber else "customer"

        # Prepare response data
        response_data = {
            "access_token": token,
            "token_type": "bearer",
            "role": role,
            "user_id": _user.id,
            "phone_number": _user.phone_number,
            "username": _user.username,
            "expires_on_logout": True
        }
        
        # Add barber-specific information if user is a barber
        if _user.is_barber:
            response_data.update({
                "shop_name": _user.shop_name,
                "shop_address": _user.shop_address,
                "shop_image_url": _user.shop_image_url,
                "license_number": _user.license_number
            })

        return ResponseSchema(
            code="200",
            status="OK",
            message="Login successful",
            result=response_data
        ).dict(exclude_none=True)
        
    except Exception as error:
        print(f"Login error: {error}")
        return ResponseSchema(
            code="500", 
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.post('/logout')
async def logout(
    request: LogoutRequest = LogoutRequest(),
    db: Session = Depends(get_db),
    current_session: UserSession = Depends(get_current_session),
    current_user: Users = Depends(get_current_user)
):
    """Logout from current session or all sessions"""
    try:
        if request.logout_all_devices:
            # Logout from all devices
            SessionRepo.invalidate_all_user_sessions(db, current_user.id)
            message = "Logged out from all devices successfully"
        else:
            # Logout from current session only
            SessionRepo.invalidate_session(db, current_session.session_token)
            message = "Logged out successfully"
        
        return ResponseSchema(
            code="200",
            status="OK",
            message=message
        ).dict(exclude_none=True)
        
    except Exception as error:
        print(f"Logout error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.get('/sessions', response_model=ActiveSessionsResponse)
async def get_active_sessions(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session)
):
    """Get all active sessions for the current user"""
    try:
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).order_by(UserSession.last_accessed.desc()).all()
        
        session_info = []
        for session in sessions:
            session_info.append(SessionInfo(
                session_id=session.id,
                device_info=session.device_info,
                ip_address=session.ip_address,
                created_at=session.created_at,
                last_accessed=session.last_accessed,
                is_current=(session.id == current_session.id)
            ))
        
        return ActiveSessionsResponse(
            total_sessions=len(session_info),
            sessions=session_info
        )
        
    except Exception as error:
        print(f"Get sessions error: {error}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete('/sessions/{session_id}')
async def terminate_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session)
):
    """Terminate a specific session"""
    try:
        # Find the session
        session = db.query(UserSession).filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Don't allow terminating current session (use logout instead)
        if session.id == current_session.id:
            return ResponseSchema(
                code="400",
                status="Bad Request",
                message="Cannot terminate current session. Use logout endpoint instead."
            ).dict(exclude_none=True)
        
        # Terminate the session
        session.is_active = False
        db.commit()
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Session terminated successfully"
        ).dict(exclude_none=True)
        
    except HTTPException:
        raise
    except Exception as error:
        print(f"Terminate session error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.post('/change-password')
async def change_password(
    request: ChangePassword, 
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session)
):
    """Change password and invalidate all other sessions"""
    try:
        # Verify current password
        if not pwd_context.verify(request.current_password, current_user.password):
            return ResponseSchema(
                code="400",
                status="Bad Request",
                message="Current password is incorrect"
            ).dict(exclude_none=True)
        
        # Check if new password is different from current password
        if pwd_context.verify(request.new_password, current_user.password):
            return ResponseSchema(
                code="400",
                status="Bad Request",
                message="New password must be different from current password"
            ).dict(exclude_none=True)
        
        # Update password
        current_user.password = pwd_context.hash(request.new_password)
        db.commit()
        
        # Invalidate all other sessions except current one for security
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.id != current_session.id,
            UserSession.is_active == True
        ).update({"is_active": False})
        db.commit()
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Password changed successfully. All other sessions have been logged out."
        ).dict(exclude_none=True)
        
    except Exception as error:
        print(f"Change password error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.get('/profile')
async def get_profile(
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Get current user profile"""
    try:
        profile_data = {
            "user_id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "is_barber": current_user.is_barber,
            "created_at": current_user.create_date  # Fixed: use create_date instead of created_at
        }
        
        # Add barber-specific information if user is a barber
        if current_user.is_barber:
            profile_data.update({
                "shop_name": current_user.shop_name,
                "shop_address": current_user.shop_address,
                "shop_image_url": current_user.shop_image_url,
                "license_number": current_user.license_number
            })
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Profile retrieved successfully",
            result=profile_data
        ).dict(exclude_none=True)
        
    except Exception as error:
        print(f"Get profile error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.get('/verify-token')
async def verify_token(
    current_user: Users = Depends(get_current_user),
    current_session: UserSession = Depends(get_current_session)
):
    """Verify if the current token is valid"""
    try:
        role = "barber" if current_user.is_barber else "customer"
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Token is valid",
            result={
                "user_id": current_user.id,
                "username": current_user.username,
                "role": role,
                "session_id": current_session.id,
                "is_active": current_session.is_active
            }
        ).dict(exclude_none=True)
        
    except Exception as error:
        print(f"Verify token error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)