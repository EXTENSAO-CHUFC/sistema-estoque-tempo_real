#!/usr/bin/env python3
"""View/entrypoint FastAPI. Regras e persistência ficam em app/."""
from fastapi import FastAPI
from app.controllers.web_controller import router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Estoque - Interface do Operador")
app.include_router(router)
app.mount(
    "/static",
    StaticFiles(directory="app/web/static"),
    name="static",
)