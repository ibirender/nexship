import bcrypt
import secrets
import random
import os
import razorpay
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from mangum import Mangum


from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app import models, schemas, crud
from app.database import engine, get_db
from app.email_service import send_reset_email


# ===============================
# SECURITY
# ===============================
security = HTTPBearer()
fake_token_db = {}  # dev-only token store

# load env and configure payments
load_dotenv()
RAZORPAY_KEY = os.getenv("RAZORPAY_KEY")
RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET")
if not RAZORPAY_KEY or not RAZORPAY_SECRET:
    # warnings can be printed but not raise
    print("Warning: razorpay credentials missing in .env")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))


# ===============================
# DATABASE
# ===============================
models.Base.metadata.create_all(bind=engine)


# ===============================
# APP
# ===============================
app = FastAPI(
    title="Product Management API",
    description="Product Management System",
    version="1.0.0"
)

# serve frontend static files under /static and index at root
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

# safely mount static files if the directory exists (for local dev)
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_path, 'index.html'))

handler = Mangum(app)

# CORS (for your frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # in prod, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# ORDER STATUS FLOW
# ===============================
ORDER_STATUS_FLOW = {
    "pending": ["completed", "cancelled"],
    "completed": [],
    "cancelled": []
}


# =========================================================
# REGISTER
# =========================================================
@app.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(400, "Username already registered")

    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(400, "Email already registered")

    return crud.create_user(db=db, user=user)


# =========================================================
# LOGIN
# =========================================================
@app.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, user_data.username, user_data.password)

    if not user:
        raise HTTPException(401, "Incorrect username or password")

    token = secrets.token_hex(16)
    fake_token_db[token] = user.username

    return {"access_token": token, "token_type": "bearer"}


# =========================================================
# CURRENT USER
# =========================================================
@app.get("/users/me", response_model=schemas.UserResponse)
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


# =========================================================
# UPDATE PROFILE
# =========================================================
@app.put("/users/me")
def update_profile(
    user_update: schemas.UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for key, value in user_update.dict(exclude_unset=True).items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# =========================================================
# CHANGE PASSWORD
# =========================================================
@app.post("/change-password")
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
    tokens_to_delete = [
        t for t, u in fake_token_db.items() if u == current_user.username
    ]
    for t in tokens_to_delete:
        fake_token_db.pop(t)

    return {
        "message": "Password changed successfully",
        "tokens_deleted": len(tokens_to_delete),
    }


# =========================================================
# LOGOUT
# =========================================================
@app.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    if token in fake_token_db:
        fake_token_db.pop(token)
        return {"message": "Logged out successfully"}

    raise HTTPException(401, "Token already expired or invalid")


# =========================================================
# ROOT
# =========================================================
# Root is handled by serve_index if frontend exists, otherwise fallback is handled below or by Vercel


# =========================================================
# PRODUCTS
# =========================================================
@app.post("/products/", response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db=db, product=product)


@app.get("/products/", response_model=List[schemas.ProductResponse])
def read_products(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(models.Product).offset(skip).limit(limit).all()


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.put("/products/{product_id}")
def update_product(product_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    return crud.update_product(db, product_id, product)


@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    return crud.delete_product(db, product_id)


# =========================================================
# FORGOT PASSWORD
# =========================================================
@app.post("/forgot-password")
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


# =========================================================
# RESET PASSWORD
# =========================================================
@app.post("/reset-password")
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


# =========================================================
# CREATE ORDER
# =========================================================
@app.post("/orders")
def create_order(
    order: schemas.OrderCreate,
    use_wallet: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_order = models.Order(user_id=current_user.id, status="pending", used_wallet=use_wallet)
    db.add(db_order)
    db.flush()

    total_price = 0

    for item in order.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id
        ).first()

        if not product:
            raise HTTPException(404, "Product not found")

        if product.stock < item.quantity:
            raise HTTPException(400, "Not enough stock")

        subtotal = product.price * item.quantity
        total_price += subtotal

        db.add(models.OrderItem(
            order_id=db_order.id,
            product_id=product.id,
            quantity=item.quantity,
            price_at_purchase=product.price
        ))

    db_order.total_price = total_price

    # wallet payment path – mark for later deduction, don't change balance or stock yet
    if use_wallet:
        # still validate sufficient funds but don't debit now
        if current_user.balance < total_price:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        # leave order pending; admin approval will debit and deduct stock
        db.commit()
        db.refresh(db_order)

        return {
            "order_id": db_order.id,
            "total": total_price,
            "message": "Order created successfully; pay with wallet when admin approves"
        }

    # non-wallet path: create a Razorpay order as soon as we calculate the total
    db.commit()

    amount_paise = int(total_price * 100)
    try:
        rz_order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"order_{db_order.id}",
        })
    except Exception as e:
        # if Razorpay call fails, rollback db changes and propagate
        db.rollback()
        raise HTTPException(status_code=500, detail="Payment gateway error")

    # store razorpay order id for later verification
    db_order.razorpay_order_id = rz_order.get("id")
    db.commit()
    db.refresh(db_order)

    return {
        "order_id": db_order.id,
        "total": total_price,
        "razorpay_order": rz_order,
        "message": "Order created successfully, proceed to payment"
    }

# =========================================================
# GET MY ORDERS
# =========================================================
@app.get("/orders")
def my_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        orders = db.query(models.Order).filter(
            models.Order.user_id == current_user.id
        ).all()

        result = []

        for order in orders:
            order_data = {
                "order_id": order.id,
                "total_price": order.total_price,
                "created_at": order.created_at,
                "status": order.status,
                "used_wallet": order.used_wallet,
                "razorpay_order_id": order.razorpay_order_id,
                "payment_status": order.payment_status,
                "items": []
            }

            for item in order.items:
                order_data["items"].append({
                    "product_name": item.product.name if item.product else "Deleted Product",
                    "quantity": item.quantity,
                    "price_at_purchase": item.price_at_purchase,
                    "subtotal": item.quantity * item.price_at_purchase
                })

            result.append(order_data)

        return result

    except Exception as e:
        print(f"Orders error: {e}")  # Check your terminal for the real error
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/admin/orders")
def admin_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    try:
        orders = db.query(models.Order).all()
        result = []

        for order in orders:
            user = db.query(models.User).filter(models.User.id == order.user_id).first()

            order_data = {
                "order_id": order.id,
                "user_id": order.user_id,
                "username": user.username if user else "Deleted User",
                "total_price": order.total_price,
                "created_at": order.created_at,
                "status": order.status,
                "used_wallet": order.used_wallet,
                "razorpay_order_id": order.razorpay_order_id,
                "payment_status": order.payment_status,
                "items": []
            }

            for item in order.items:
                order_data["items"].append({
                    "product_name": item.product.name if item.product else "Deleted Product",
                    "quantity": item.quantity,
                    "price_at_purchase": item.price_at_purchase,
                    "subtotal": item.quantity * item.price_at_purchase
                })

            result.append(order_data)

        return result

    except Exception as e:
        print(f"ADMIN ORDERS ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))# =========================================================
# UPDATE ORDER STATUS
# =========================================================
@app.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    order = db.query(models.Order).filter(
        models.Order.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    current_status = order.status

    if new_status not in ORDER_STATUS_FLOW.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from {current_status} to {new_status}"
        )

    # confirm order → deduct wallet
    if current_status == "pending" and new_status == "completed":

        order_owner = db.query(models.User).filter(
            models.User.id == order.user_id
        ).first()

        # only deduct from wallet if the order was placed using wallet balance
        if order.used_wallet:
            if order_owner.balance < order.total_price:
                raise HTTPException(status_code=400, detail="Insufficient balance")

            order_owner.balance -= order.total_price
            order.payment_status = "completed"

        # reduce stock for each item since order is now finalized
        for item in order.items:
            product = item.product
            if product:
                product.stock -= item.quantity

    # cancel order → restore stock
    if current_status == "pending" and new_status == "cancelled":

        for item in order.items:
            product = item.product
            if product:
                product.stock += item.quantity

    order.status = new_status

    db.commit()
    db.refresh(order)

    return {
        "message": f"Order status updated to {new_status}",
        "order_id": order.id
    }


# =========================================================
# RAZORPAY PAYMENT VERIFICATION
# =========================================================
@app.post("/payment/verify")
def verify_payment(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session = Depends(get_db),
):
    params_dict = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature,
    }

    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    order = db.query(models.Order).filter(
        models.Order.razorpay_order_id == razorpay_order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.razorpay_payment_id = razorpay_payment_id
    order.payment_status = "completed"
    # leave order.status as "pending"; admin will confirm before completing

    # wallet is not affected here

    db.commit()

    return {"message": "Payment verified and order completed"}