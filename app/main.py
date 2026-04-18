from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from . import templates
from app.routes import api_router
from .auth import manager

app = FastAPI()

# Glue routers to the app
app.include_router(api_router)

# Mount static files to the app
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def main_page(request: Request, user=Depends(manager.optional)):
    # Request is required fo Jinja
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"offers": [], "user": user}
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
