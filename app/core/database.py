# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = "postgresql://neondb_owner:npg_jvnX5EcJke8x@ep-sweet-block-a1dfz75q-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    print("Connected to default database URL")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# Create session factory(basically session generator h baad m just session local)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)#blue print keh skte ho 

# Create Base class - THIS IS WHAT MODELS.PY NEEDS
Base = declarative_base()# Later, any class that uses this Base becomes a database table.

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()