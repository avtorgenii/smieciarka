from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text, Row
from sqlalchemy.ext.asyncio import AsyncConnection

from app.database import get_db
from app import templates
from app.routes.auth import manager

# Creating router
router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/")
async def profile_page(request: Request, user=Depends(manager), db=Depends(get_db)):
    # Fetch user's own offers
    offers_query = text("SELECT id, title, created_at FROM offers WHERE owner_id = :uid")
    offers_res = await db.execute(offers_query, {"uid": user.id})
    my_offers = offers_res.fetchall()

    # Fetch user's reservations
    res_query = text("""
                     SELECT r.id, r.status, r.expiry_date, o.title as offer_title, o.id as offer_id
                     FROM reservations r
                              JOIN offers o ON r.offer_id = o.id
                     WHERE r.user_id = :uid
                     ORDER BY r.created_at DESC
                     """)
    res_data = await db.execute(res_query, {"uid": user.id})
    my_reservations = res_data.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": user,
            "my_offers": my_offers,
            "my_reservations": my_reservations
        }
    )
