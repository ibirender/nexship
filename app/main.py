import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.core.database import engine
from app.core import models
from app.routers import auth, products, orders, payments

from contextlib import asynccontextmanager

# ===============================
# LIFESPAN (STURDY INITIALIZATION)
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # DATABASE: Create tables on startup only
    # In serverless (Vercel), this may still be tricky if cold start is slow,
    # but it's much safer than top-level import-time execution.
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database initialization error: {e}")
    yield

# ===============================
# APP INITIALIZATION
# ===============================
app = FastAPI(
    title="Product Management API",
    description="Product Management System",
    version="1.0.0",
    lifespan=lifespan
)

# serve frontend static files under /static and index at root
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Use absolute path or relative to this file
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, 'frontend')

# safely mount static files if the directory exists
if os.path.exists(frontend_path):
    print(f"Found frontend at {frontend_path}")
    # check for index.html before mounting
    index_file = os.path.join(frontend_path, 'index.html')
    if os.path.exists(index_file):
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")

        @app.get("/")
        def serve_index():
            return FileResponse(index_file)
    else:
        print(f"Warning: {index_file} not found")
else:
    print(f"Warning: Frontend directory {frontend_path} not found")

handler = Mangum(app)

# CORS (for your frontend)
origins = [
    "https://nexshipp.vercel.app",
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# ROUTERS
# ===============================
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)