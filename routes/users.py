from fastapi import APIRouter, Depends, HTTPException
from models.users import TokenResponse, Register, Login, ResponseSchema
from sqlalchemy.orm import Session
from config import get_db
from passlib.context import CryptContext
from repository.users import UserRepo, JWTRepo
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
        # Check if user already exists
        existing_user = UserRepo.find_by_username(db, Users, request.username)
        if existing_user:
            return ResponseSchema(
                code="400", 
                status="Error", 
                message="Username already exists"
            ).dict(exclude_none=True)

        # Handle image upload if provided (reuse existing shop_image_url field)
        final_image_url = None
        if request.is_barber and request.shop_image_url:
            # Check if it's a base64 string (from mobile) or already a URL
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
                # It's already a URL, use as-is
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
        
        # Auto-login after successful signup
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

@router.post('/login')
async def login(request: Login, db: Session = Depends(get_db)):
    try:
        _user = UserRepo.find_by_username(db, Users, request.username)

        if not _user or not pwd_context.verify(request.password, _user.password):
            return ResponseSchema(
                code="400", 
                status="Bad Request", 
                message="Invalid credentials"
            ).dict(exclude_none=True)

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
                "shop_image_url": _user.shop_image_url
            }
        ).dict(exclude_none=True)
    except Exception as error:
        print(f"Login error: {error}")
        return ResponseSchema(
            code="500", 
            status="Error", 
            message="Internal Server Error"
        ).dict(exclude_none=True)