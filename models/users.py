from pydantic import BaseModel
from typing import Optional, Any

class Register(BaseModel):
    username: str
    password: str
    email: str
    phone_number: str
    first_name: str
    last_name: str
    is_barber: bool = False
    shop_name: Optional[str] = None
    shop_address: Optional[str] = None
    shop_image_url: Optional[str] = None  # Base64 image string from mobile
    license_number: Optional[str] = None  # New license number field

class Login(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class ResponseSchema(BaseModel):
    code: str
    status: str
    message: str
    result: Optional[Any] = None