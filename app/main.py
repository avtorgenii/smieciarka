from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from . import templates
from app.routes import api_router
from .auth import manager
from .database import get_db
from sqlalchemy.ext.asyncio import AsyncConnection

app = FastAPI()

# Glue routers to the app
app.include_router(api_router)

# Mount static files to the app
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def main_page(request: Request, user=Depends(manager.optional), db: AsyncConnection = Depends(get_db)):
    query = text("""
                 SELECT id, name
                 FROM categories
                 """)

    result = await db.execute(query, {})

    categories = result.fetchall()

    # Request is required fo Jinja
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"categories": categories, "user": user}
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )
