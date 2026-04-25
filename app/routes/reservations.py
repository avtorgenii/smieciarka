from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import text, Row
from sqlalchemy.ext.asyncio import AsyncConnection

from app.database import get_db
from app import templates
from app.routes.auth import manager

# Creating router
router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/{offer_id}", status_code=201)
async def create_reservation(
        request: Request,
        offer_id: int,
        user: Row = Depends(manager),  # User from token in cookies
        db: AsyncConnection = Depends(get_db)
):
    # 3. INSERT INTO reservations (offer_id, user_id, status) ...

    # Check if there are existing reservations
    query = text("""
                 SELECT EXISTS (SELECT 1
                                FROM reservations
                                WHERE offer_id = :offer_id
                                  AND status IN ('ACTIVE', 'FULFILLED'))
                 """)

    result = await db.execute(query, {"offer_id": offer_id})
    is_reserved = result.scalar()  # Returns True or False

    if is_reserved:
        return templates.TemplateResponse(
            request=request,
            name="reservation_status.html",
            context={
                "user": user,
                "success": False,
                "message": "Too late! Someone else just grabbed this item."
            }
        )

    else:
        query = text("""
                     INSERT INTO reservations (offer_id, user_id, status)
                     VALUES (:offer_id, :user_id, :status)
                     RETURNING id
                     """)

        try:
            result = await db.execute(query, {"offer_id": offer_id, "user_id": user.id, "status": "PENDING"})
            reservation_id = result.scalar()  # Get id of freshly created reservation
            await db.commit()
        except Exception as e:
            print(f"Error during reservation: {e}")
            raise HTTPException(status_code=400, detail="Failed to reserve this offer, please try again :()")

        return templates.TemplateResponse(
            request=request,
            name="reservation_status.html",
            context={
                "user": user,
                "success": True,
                "message": "Item reserved successfully. Author has 24 hours to accept your reservation",
                "reservation_id": reservation_id,
            }
        )
