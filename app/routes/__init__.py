from fastapi import APIRouter
from app.routes import offers, auth

api_router = APIRouter()

# Combine all routers
api_router.include_router(offers.router, tags=["offers"])
api_router.include_router(auth.router, tags=["auth"])
