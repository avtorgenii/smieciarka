from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from . import templates
from app.routes import api_router

app = FastAPI()

# Glue routers to the app
app.include_router(api_router)

# Mount static files to the app
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
async def read_root(request: Request):
    # Передаем request обязательно — это нужно для Jinja
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Śmieciarka"}
    )