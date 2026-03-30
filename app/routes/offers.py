from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from app.database import get_db
from app import templates

# Creating router
router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/", response_class=HTMLResponse)
async def list_offers(request: Request, db: AsyncConnection = Depends(get_db)):
    query = text("SELECT id, title, price FROM offers")
    result = await db.execute(query)

    offers = result.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"offers": offers}
    )