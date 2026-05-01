from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.compare import router as compare_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.records import router as records_router
from app.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(records_router, prefix="/api")
app.include_router(compare_router, prefix="/api")
