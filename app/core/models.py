# app/models.py
from datetime import datetime
from typing import List
from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from pydantic import BaseModel

class User(Base):#inherit kr rha h Base se, jiska matlab h ki ye class ek database table ban jayegi
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_admin = Column(Boolean, default=False)  # Admin flag for role-based access control
    # reset_token = Column(String(255), nullable=True)  # Token for password reset functionality
    # reset_token_expires = Column(DateTime, nullable=True)
    otp = Column(String(6), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    balance = Column(Float, default=0)
    
    orders = relationship("Order", back_populates="user")
    
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String(50), nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    stock=Column(Integer, default=0)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_price = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("OrderItem", backref="order")
    user = relationship("User", back_populates="orders")
    status = Column(String, default="pending")  # pending / completed / cancelled
    # payment gateway fields
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    payment_status = Column(String(50), default="pending")
    used_wallet = Column(Boolean, default=False)  # whether user opted to pay from wallet
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_at_purchase = Column(Float)

    product = relationship("Product")

class UserToken(Base):
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    status = Column(String(50), default="pending") # pending / completed / failed
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

