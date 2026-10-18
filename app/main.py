import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.openapi import API_DESCRIPTION, OPENAPI_TAGS
from app.database import Base, engine
from app.models import (  # noqa: F401
    dining_table,
    model_category,
    model_dish,
    model_email_verification_token,
    model_invoice,
    model_order,
    model_order_item,
    model_password_reset_token,
    model_social_account,
    model_user,
    reservation,
)
from app.routers import (
    auth,
    reservations,
    router_2fa,
    router_category,
    router_dish,
    router_email_verification,
    router_export,
    router_invoice,
    router_order,
    router_password,
    router_stats,
    router_user,
    tables,
    websocket_kitchen,
)
from app.services.keep_awake import keep_awake_configured, start_keep_awake

setup_logging()
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if keep_awake_configured(settings.KEEP_AWAKE_ENABLED, settings.KEEP_AWAKE_URL):
        start_keep_awake(settings.KEEP_AWAKE_URL, settings.KEEP_AWAKE_MINUTES)
    yield


app = FastAPI(
    title="Resto API",
    version="1.0.0",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip()
                   for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(router_2fa.router)
app.include_router(router_password.router)
app.include_router(router_email_verification.router)
app.include_router(router_password.invite_router)
app.include_router(router_2fa.me_router)
app.include_router(router_user.me_router)
app.include_router(router_user.router)
app.include_router(router_category.router)
app.include_router(router_dish.router)
app.include_router(router_order.router)
app.include_router(router_invoice.router)
app.include_router(router_export.router)
app.include_router(router_stats.router)
app.include_router(tables.router)
app.include_router(reservations.router)
app.include_router(websocket_kitchen.router)


@app.get("/")
def root():
    return {"message": "API Resto working"}


@app.get("/health")
def health():
    return {"status": "ok", "commit": os.getenv("RENDER_GIT_COMMIT")}
