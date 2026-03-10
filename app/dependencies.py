import os
import razorpay
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.core import models
from app.services import crud
from app.core.database import get_db

load_dotenv()

# ===============================
# SECURITY & AUTH STATE
# ===============================
security = HTTPBearer()
fake_token_db = {}  # dev-only token store

# ===============================
# RAZORPAY SETUP
# ===============================
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")

razorpay_client = None
if RAZORPAY_KEY and RAZORPAY_SECRET:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))
else:
    print("Warning: Razorpay credentials missing")

# ===============================
# DEPENDENCIES
# ===============================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    if token not in fake_token_db:
        raise HTTPException(401, "Invalid or expired token")

    username = fake_token_db[token]
    user = crud.get_user_by_username(db, username)

    if not user:
        raise HTTPException(401, "User not found")

    return user
