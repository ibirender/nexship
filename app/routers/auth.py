import bcrypt
import secrets
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core import schemas, models
from app.services import crud
from app.core.database import get_db
from app.services.email_service import send_reset_email
from app.dependencies import security, get_current_user

router = APIRouter(tags=["Authentication & Users"])

@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(400, "Username already registered")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(400, "Email already registered")

    return crud.create_user(db=db, user=user)

@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, user_data.username, user_data.password)

    if not user:
        raise HTTPException(401, "Incorrect username or password")

    token_str = secrets.token_hex(16)
    db_token = models.UserToken(token=token_str, user_id=user.id)
    db.add(db_token)
    db.commit()

    return {"access_token": token_str, "token_type": "bearer"}

@router.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_route(
    current_user: models.User = Depends(get_current_user),
):
    return current_user

@router.put("/users/me")
def update_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/change-password")
def change_password(
    password_data: schemas.ChangePassword,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not bcrypt.checkpw(
        password_data.current_password.encode(),
        current_user.hashed_password.encode(),
    ):
        raise HTTPException(400, "Current password incorrect")

    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(400, "Passwords do not match")

    new_hash = bcrypt.hashpw(password_data.new_password.encode(), bcrypt.gensalt())
    current_user.hashed_password = new_hash.decode()

    db.commit()
    db.refresh(current_user)

    # invalidate all tokens for this user
    db.query(models.UserToken).filter(models.UserToken.user_id == current_user.id).delete()
    db.commit()

    return {
        "message": "Password changed successfully",
    }

@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token_str = credentials.credentials

    token_record = db.query(models.UserToken).filter(models.UserToken.token == token_str).first()
    if token_record:
        db.delete(token_record)
        db.commit()
        return {"message": "Logged out successfully"}

    raise HTTPException(401, "Token already expired or invalid")

@router.post("/forgot-password")
def forgot_password(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return {"message": "If email exists reset link sent"}

    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=30)

    db.commit()
    background_tasks.add_task(send_reset_email, email, otp)

    return {"message": "OTP sent to email"}

@router.post("/reset-password")
def reset_password(otp: str, new_password: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.otp == otp).first()

    if not user:
        raise HTTPException(400, "Invalid OTP")

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(400, "OTP expired")

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    user.hashed_password = hashed.decode()
    user.otp = None
    user.otp_expiry = None

    db.commit()
    return {"message": "Password updated"}
