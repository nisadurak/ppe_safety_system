import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as ui_router


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="PPE Safety System")


app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

app.mount(
    "/uploads",
    StaticFiles(directory=os.path.join(BASE_DIR, "uploads")),
    name="uploads",
)

# Tüm route'lar
app.include_router(ui_router)
