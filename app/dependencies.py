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
    token_str = credentials.credentials

    token_record = db.query(models.UserToken).filter(models.UserToken.token == token_str).first()

    if not token_record:
        raise HTTPException(401, "Invalid or expired token")

    user = token_record.user

    if not user:
        raise HTTPException(401, "User not found")

    return user
