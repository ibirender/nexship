from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional


# =========================
# USER SCHEMAS
# =========================

class UserBase(BaseModel):
    email: EmailStr
    username: str


class ChangePassword(BaseModel):
    """Password change ke liye schema"""
    current_password: str
    new_password: str
    confirm_password: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    is_admin: bool
    balance: float

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


# =========================
# PRODUCT SCHEMAS
# =========================

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category: Optional[str] = None
    is_available: Optional[bool] = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================
# ORDER SCHEMAS
# =========================

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]