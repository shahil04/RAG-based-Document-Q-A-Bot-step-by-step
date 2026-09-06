from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.connection import get_db
from app.database.models import User
from app.schemas.auth import (UserRegister,UserResponse)

router = APIRouter(prefix="/api/auth",tags=["Authentication"])

@router.post("/register",response_model=UserResponse,status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister,db: Session = Depends(get_db)):
    existing_user = (db.query(User).filter(User.email == user_data.email).first())

    if existing_user:
        raise HTTPException(status_code=400,detail="Email already registered")

    new_user = User(name=user_data.name,email=user_data.email,
                    password_hash=hash_password(user_data.password))

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# login api add
from fastapi.security import OAuth2PasswordBearer
from app.core.security import (verify_password,create_access_token)

from app.schemas.auth import (UserLogin,TokenResponse)
@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    valid_password = verify_password(
        user_data.password,
        user.password_hash
    )

    if not valid_password:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }