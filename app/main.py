import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.core.database import engine
from app.core import models
from app.routers import auth, products, orders, payments

# ===============================
# DATABASE
# ===============================
models.Base.metadata.create_all(bind=engine)

# ===============================
# APP INITIALIZATION
# ===============================
app = FastAPI(
    title="Product Management API",
    description="Product Management System",
    version="1.0.0"
)

# serve frontend static files under /static and index at root
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
# ROUTERS
# ===============================
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)