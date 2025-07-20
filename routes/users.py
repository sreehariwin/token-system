# routes/users.py - Updated login to use phone_number

from fastapi import APIRouter, Depends, HTTPException
from models.users import TokenResponse, Register, Login, ResponseSchema, ChangePassword
from sqlalchemy.orm import Session
from config import get_db
from passlib.context import CryptContext
from repository.users import UserRepo, JWTRepo, get_current_user
from tables.users import Users
from utils.cloudinary_helper import upload_base64_image

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

@router.post('/signup')
async def signup(request: Register, db: Session = Depends(get_db)):
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
        
        # Auto-login after successful signup (using username for JWT)
        token = JWTRepo.generate_token({'sub': _user.username})
        role = "barber" if _user.is_barber else "customer"
        
        return ResponseSchema(
            code="200", 
            status="OK", 
            message="User registered and logged in successfully",
            result={
                "access_token": token,
                "token_type": "bearer",
                "role": role,
                "user_id": _user.id,
                "shop_image_url": final_image_url
            }
        ).dict(exclude_none=True)
        
    except Exception as e:
        print(f"Signup error: {e}")
        return ResponseSchema(
            code="500", 
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.post('/change-password')
async def change_password(
    request: ChangePassword, 
    db: Session = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    """
    Change password for authenticated user
    """
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
        
        # Hash new password and update
        new_password_hash = pwd_context.hash(request.new_password)
        UserRepo.update_user_password(db, current_user, new_password_hash)
        
        return ResponseSchema(
            code="200",
            status="OK",
            message="Password changed successfully"
        ).dict(exclude_none=True)
        
    except ValueError as ve:
        # Handle Pydantic validation errors
        return ResponseSchema(
            code="400",
            status="Bad Request",
            message=str(ve)
        ).dict(exclude_none=True)
    except Exception as error:
        print(f"Change password error: {error}")
        return ResponseSchema(
            code="500",
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.get('/profile')
async def get_profile(current_user: Users = Depends(get_current_user)):
    """
    Get current user's profile information
    """
    try:
        return ResponseSchema(
            code="200",
            status="OK",
            message="Profile retrieved successfully",
            result={
                "user_id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "phone_number": current_user.phone_number,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "is_barber": current_user.is_barber,
                "shop_name": current_user.shop_name,
                "shop_address": current_user.shop_address,
                "shop_image_url": current_user.shop_image_url,
                "license_number": current_user.license_number,
                "created_at": current_user.create_date
            }
        ).dict(exclude_none=True)
    except Exception as error:
        print(f"Get profile error: {error}")
        return ResponseSchema(
            code="500",
            status="Error",
            message="Internal Server Error"
        ).dict(exclude_none=True)

@router.post('/login')
async def login(request: Login, db: Session = Depends(get_db)):
    try:
        # Find user by phone number instead of username
        _user = UserRepo.find_by_phone_number(db, Users, request.phone_number)

        if not _user or not pwd_context.verify(request.password, _user.password):
            return ResponseSchema(
                code="400", 
                status="Bad Request", 
                message="Invalid phone number or password"  # Updated error message
            ).dict(exclude_none=True)

        # Generate token using username (keeping JWT payload structure the same)
        token = JWTRepo.generate_token({'sub': _user.username})
        role = "barber" if _user.is_barber else "customer"

        return ResponseSchema(
            code="200",
            status="OK",
            message="Login successful",
            result={
                "access_token": token,
                "token_type": "bearer",
                "role": role,
                "user_id": _user.id,
                "shop_image_url": _user.shop_image_url,
                "phone_number": _user.phone_number  # Include phone number in response
            }
        ).dict(exclude_none=True)
    except Exception as error:
        print(f"Login error: {error}")
        return ResponseSchema(
            code="500", 
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)