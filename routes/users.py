# routes/users.py - Updated with session-based authentication and profile update
from fastapi import APIRouter, Depends, HTTPException, Request,Query,status
from models.users import (
    TokenResponse, Register, Login, ResponseSchema, ChangePassword,
    ActiveSessionsResponse, LogoutRequest, SessionInfo, UpdateProfileRequest
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
from datetime import datetime
from utils.notifications import NotificationService
from fastapi.exceptions import RequestValidationError


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

@router.post('/signup')  # KEEP YOUR EXISTING ROUTE NAME
async def signup(request: Register, req: Request, db: Session = Depends(get_db)):
    try:
        # Your existing validation logic (don't change)
        existing_user_by_username = UserRepo.find_by_username(db, Users, request.username)
        if existing_user_by_username:
            return ResponseSchema(
                code="400", 
                status="Error", 
                message="Username already exists"
            ).dict(exclude_none=True)

        existing_user_by_phone = UserRepo.find_by_phone_number(db, Users, request.phone_number)
        if existing_user_by_phone:
            return ResponseSchema(
                code="400", 
                status="Error", 
                message="Phone number already exists"
            ).dict(exclude_none=True)

        # Your existing image upload logic (don't change)
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

        # Create new user - ADD NOTIFICATION FIELDS HERE:
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
            license_number=request.license_number if request.is_barber else None,
            shop_status=request.shop_status if request.is_barber else None,
            notifications_enabled=True,  # Default to enabled
            fcm_token=None  # Will be set later when app connects
        )

        # Your existing logic (don't change the rest)
        UserRepo.insert(db, _user)

        device_info, ip_address = get_client_info(req)
        session = SessionRepo.create_session(db, _user.id, device_info, ip_address)

        token = JWTRepo.generate_session_token(session.session_token)
        role = "barber" if _user.is_barber else "customer"

        response_data = {
            "access_token": token,
            "token_type": "bearer",
            "role": role,
            "user_id": _user.id,
            "phone_number": _user.phone_number,
            "username": _user.username,
            "expires_on_logout": True
        }

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
                "license_number": current_user.license_number,
                "shop_status":current_user.shop_status
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

@router.put('/profile')
async def update_profile(
    request: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Update user profile information"""
    try:
        updated_fields = []
        
        # Check if phone number or email are being changed and if they're already taken
        if request.phone_number and request.phone_number != current_user.phone_number:
            existing_phone = UserRepo.find_by_phone_number(db, Users, request.phone_number)
            if existing_phone and existing_phone.id != current_user.id:
                return ResponseSchema(
                    code="400",
                    status="Bad Request",
                    message="Phone number is already registered to another account"
                ).dict(exclude_none=True)
        
        if request.username and request.username != current_user.username:
            existing_username = UserRepo.find_by_username(db, Users, request.username)
            if existing_username and existing_username.id != current_user.id:
                return ResponseSchema(
                    code="400",
                    status="Bad Request",
                    message="Username is already taken"
                ).dict(exclude_none=True)
        
        if request.email and request.email != current_user.email:
            existing_email = db.query(Users).filter(Users.email == request.email).first()
            if existing_email and existing_email.id != current_user.id:
                return ResponseSchema(
                    code="400",
                    status="Bad Request",
                    message="Email is already registered to another account"
                ).dict(exclude_none=True)
        
        # Update basic profile fields
        if request.first_name is not None and request.first_name != current_user.first_name:
            current_user.first_name = request.first_name
            updated_fields.append("first_name")
        
        if request.last_name is not None and request.last_name != current_user.last_name:
            current_user.last_name = request.last_name
            updated_fields.append("last_name")
        
        if request.email is not None and request.email != current_user.email:
            current_user.email = request.email
            updated_fields.append("email")
        
        if request.phone_number is not None and request.phone_number != current_user.phone_number:
            current_user.phone_number = request.phone_number
            updated_fields.append("phone_number")
        
        if request.username is not None and request.username != current_user.username:
            current_user.username = request.username
            updated_fields.append("username")

        if request.shop_status is not None and request.shop_status != current_user.shop_status:
                current_user.shop_status = request.shop_status
                updated_fields.append("shop_status")
        
        # Update barber-specific fields (only if user is a barber)
        if current_user.is_barber:
            if request.shop_name is not None and request.shop_name != current_user.shop_name:
                current_user.shop_name = request.shop_name
                updated_fields.append("shop_name")
            
            if request.shop_address is not None and request.shop_address != current_user.shop_address:
                current_user.shop_address = request.shop_address
                updated_fields.append("shop_address")
            
            if request.license_number is not None and request.license_number != current_user.license_number:
                current_user.license_number = request.license_number
                updated_fields.append("license_number")
            
            
            
            # Handle shop image update
            if request.shop_image_url is not None and request.shop_image_url != current_user.shop_image_url:
                final_image_url = None
                
                # If it's a base64 image or doesn't start with http, upload to Cloudinary
                if request.shop_image_url.startswith('data:image') or not request.shop_image_url.startswith('http'):
                    try:
                        final_image_url = upload_base64_image(
                            request.shop_image_url, 
                            folder=f"barbershop/{current_user.username}"
                        )
                        print(f"✅ Profile image uploaded to Cloudinary: {final_image_url}")
                    except Exception as e:
                        print(f"⚠️ Profile image upload failed: {e}")
                        return ResponseSchema(
                            code="400",
                            status="Bad Request",
                            message=f"Image upload failed: {str(e)}"
                        ).dict(exclude_none=True)
                else:
                    final_image_url = request.shop_image_url
                
                current_user.shop_image_url = final_image_url
                updated_fields.append("shop_image_url")
        else:
            # If user is not a barber but trying to update barber fields, return error
            barber_fields_provided = [request.shop_name, request.shop_address, request.shop_image_url, request.license_number, request.shop_status]
            if any(field is not None for field in barber_fields_provided):
                current_user.shop_name = None
                current_user.shop_address = None
                current_user.shop_image_url = None
                current_user.license_number = None
                current_user.shop_status = False
                updated_fields.extend(["shop_name", "shop_address", "shop_image_url", "license_number", "shop_status"])
        
        # Check if any fields were actually updated
        if not updated_fields:
            return ResponseSchema(
                code="400",
                status="Bad Request",
                message="No changes detected in the submitted data"
            ).dict(exclude_none=True)
        
        # Update the update_date timestamp
        current_user.update_date = datetime.utcnow()
        updated_fields.append("update_date")
        
        # Commit changes to database
        db.commit()
        db.refresh(current_user)
        
        # Prepare response data
        response_data = {
            "user_id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "is_barber": current_user.is_barber,
            "updated_fields": updated_fields
        }
        
        # Add barber-specific information if user is a barber
        if current_user.is_barber:
            response_data.update({
                "shop_name": current_user.shop_name,
                "shop_address": current_user.shop_address,
                "shop_image_url": current_user.shop_image_url,
                "license_number": current_user.license_number,
                "shop_status": current_user.shop_status,
            })
        
        return ResponseSchema(
            code="200",
            status="OK",
            message=f"Profile updated successfully. Updated {len(updated_fields)} fields.",
            result=response_data
        ).dict(exclude_none=True)
        
    except ValueError as ve:
        # Handle validation errors
        return ResponseSchema(
            code="400",
            status="Bad Request",
            message=str(ve)
        ).dict(exclude_none=True)
        
    except Exception as error:
        db.rollback()
        print(f"Update profile error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.put('/shop-status')
async def update_shop_status(
    is_open: bool = Query(..., description="Shop status: true for open, false for closed"),
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """Update shop open/closed status (barbers only)"""
    if not current_user.is_barber:
        raise HTTPException(status_code=403, detail="Only barbers can update shop status")
    
    current_user.shop_status = is_open
    current_user.update_date = datetime.utcnow()
    db.commit()
    
    status_text = "open" if is_open else "closed"
    return ResponseSchema(
        code="200",
        status="OK", 
        message=f"Shop status updated to {status_text}",
        result={"shop_status": is_open, "status_text": status_text}
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
    
