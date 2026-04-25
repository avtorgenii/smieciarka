from fastapi import APIRouter
from app.routes import offers, auth, profile, reservations

api_router = APIRouter()

# Combine all routers
api_router.include_router(offers.router, tags=["offers"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(profile.router, tags=["profile"])
api_router.include_router(reservations.router, tags=["reservations"])
