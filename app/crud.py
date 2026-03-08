from sqlalchemy.orm import Session
from app import models, schemas
import bcrypt


# ==============================
# USER CRUD
# ==============================

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(
        models.User.username == username
    ).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(
        models.User.email == email
    ).first()


def create_user(db: Session, user: schemas.UserCreate):

    password = user.password.strip()

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)

    db_user = models.User(
        email=user.email.strip(),
        username=user.username.strip(),
        hashed_password=hashed_password.decode("utf-8"),
        is_active=True,
        balance=0  # give starting balance so orders work
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def authenticate_user(db: Session, identifier: str, password: str):

    user = db.query(models.User).filter(
        (models.User.username == identifier) |
        (models.User.email == identifier)
    ).first()

    if not user:
        return False

    if bcrypt.checkpw(
        password.strip().encode("utf-8"),
        user.hashed_password.encode("utf-8")
    ):
        return user

    return False


# ==============================
# PRODUCT CRUD
# ==============================

def create_product(db: Session, product: schemas.ProductCreate):

    db_product = models.Product(**product.dict())

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return db_product


def get_products(db: Session, skip: int = 0, limit: int = 100):

    return db.query(models.Product)\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_product(db: Session, product_id: int):

    return db.query(models.Product)\
        .filter(models.Product.id == product_id)\
        .first()


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):

    db_product = get_product(db, product_id)

    if db_product:

        for key, value in product_update.dict(exclude_unset=True).items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)

    return db_product


def delete_product(db: Session, product_id: int):

    db_product = get_product(db, product_id)

    if db_product:
        db.delete(db_product)
        db.commit()

    return db_product