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
    shop_image_url: Optional[str] = None

class Login(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class ResponseSchema(BaseModel):
    code: str
    status: str
    message: str
    result: Optional[Any] = None