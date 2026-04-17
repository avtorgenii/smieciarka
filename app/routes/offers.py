from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from app.database import get_db
from app import templates

# Creating router
router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/", response_class=HTMLResponse)
async def list_offers(request: Request,
                      search: str | None = None,
                      category_id: int | None = None,
                      page: int = 1,
                      size: int = 20,
                      db: AsyncConnection = Depends(get_db)):
    """
    GET /offers?search=Sofa&category_id=5&limit=20&offset=0
    {
      "items": [
        {"id": 1, "title": "das Sofa", "price": 0},
        {"id": 2, "title": "der Schreibtisch", "price": 0}
      ],
      "total": 142,
      "limit": 20,
      "offset": 0
    }
    """

    sql_limit = size
    sql_offset = (page - 1) * size

    query = text("""
                 SELECT id, title, price
                 FROM offers
                 WHERE title ILIKE :search
                 ORDER BY created_at DESC
                     LIMIT :limit
                 OFFSET :offset
                 """)

    result = await db.execute(query, {
        "search": f"%{search}%" if search else "%",
        "limit": sql_limit,
        "offset": sql_offset
    })

    offers = result.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"offers": offers, "page": page, "size": size}
    )
