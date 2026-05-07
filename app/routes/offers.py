from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text, Row
from sqlalchemy.ext.asyncio import AsyncConnection
from app.routes.auth import manager

from app.database import get_db
from app import templates

# Creating router
router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_class=HTMLResponse)
async def search(request: Request,
                 search: str | None = None,
                 category_id: int | None = None,
                 page: int = 1,
                 size: int = 20,
                 user: Row = Depends(manager.optional),  # User from token in cookies
                 db: AsyncConnection = Depends(get_db)):
    """
    GET /offers?search=Sofa&category_id=5&page=1&size=20
    {
      "items": [
        {"id": 1, "title": "das Sofa", "price": 0},
        {"id": 2, "title": "der Schreibtisch", "price": 0}
      ],
      "total": 142,
      "page": 1,
      "size": 20
    }
    """

    sql_limit = size
    sql_offset = (page - 1) * size

    query = text("""
                 SELECT o.id,
                        o.title,
                        o.price,
                        o.created_at,
                        -- Take first non-null photo
                        (SELECT url FROM photos WHERE offer_id = o.id ORDER BY sort_order ASC LIMIT 1) as photo_url,
                        STRING_AGG(c.name, ', ') as categories_list -- Glue all categories into single string
                 FROM
                     -- Take all offers that could be reserved
                     (
                     SELECT o.id, o.title, o.description, o.price, o.created_at
                     FROM offers o
                     WHERE NOT EXISTS (
                             SELECT 1 FROM reservations r
                             WHERE r.offer_id = o.id
                             AND r.status IN ('ACTIVE', 'FULFILLED', 'PENDING')
                     )
                     ) as o
                     LEFT JOIN offer_categories oc
                 ON o.id = oc.offer_id
                     LEFT JOIN categories c ON oc.category_id = c.id
                 WHERE (o.title ILIKE :search_query
                    OR c.name ILIKE :search_query)
                   AND
                     (CAST (:category_id AS INTEGER) IS NULL
                    OR oc.category_id = :category_id)
                 -- Group so there would be only one row per offer
                 GROUP BY o.id, o.title, o.price, o.created_at
                 ORDER BY o.created_at DESC
                     LIMIT :limit
                 OFFSET :offset
                 """)

    result = await db.execute(query, {
        "search_query": f"%{search}%" if search else "%",
        "category_id": category_id,
        "limit": sql_limit,
        "offset": sql_offset
    })

    offers = result.fetchall()

    return templates.TemplateResponse(
        request=request,
        name="offers.html",
        context={
            "user": user,
            "offers": offers,
            "page": page,
            "size": size,
            # For pagination
            "search": search,
            "category_id": category_id,
        }
    )
