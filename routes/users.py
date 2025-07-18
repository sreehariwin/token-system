from fastapi import APIRouter, Depends
from models.users import ResponseSchema, TokenResponse, Register, Login
from sqlalchemy.orm import Session
from config import get_db
from passlib.context import CryptContext
from repository.users import UserRepo, JWTRepo
from tables.users import Users
import traceback


router = APIRouter(
    tags={"Authentication"}
)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")

#register

@router.post('/signup')
async def signup(request: Register, db:Session = Depends(get_db)):
    try:
        #insert data
        _user = Users(
            username = request.username,
            password = pwd_context.hash(request.password),
            email = request.email,
            phone_number = request.phone_number,
            first_name = request.first_name,
            last_name = request.last_name,)
        UserRepo.insert(db, _user)
        return ResponseSchema(code="200",status="OK",message="Success save date").dict(exclude_none=True)
    except Exception as error:
        print(error.args)
        return ResponseSchema(code="500",status="Error",message="Internal server Error").dict(exclude_none=True)
        

@router.post('/login')
async def login(request: Login, db: Session = Depends(get_db)):
    try: #find user by username
        _user = UserRepo.find_by_username(db, Users, request.username)

        if not pwd_context.verify(request.password, _user.password):
           return ResponseSchema(code="400", status="Bad Request", message="invalid password").dict(exclude_none=True)

        token = JWTRepo.generate_token({'sub':_user.username})
        return ResponseSchema(code="200", status="ok", message="Success login", result=TokenResponse(access_token=token, token_type="bearer").dict(exclude_none=True))   
    except Exception as error:
        error_message = str(error.args)
        print(error_message)
        return ResponseSchema(code="500",status="Error",message="Internal server Error").dict(exclude_none=True)
