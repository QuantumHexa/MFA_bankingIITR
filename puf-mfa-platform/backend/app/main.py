from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_security_settings
from app.crypto import load_or_generate_keypair
from app.database import init_db
from app.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from app.routes import admin, auth, health, users, ws

app = FastAPI(
    title="SecureVault PUF-MFA Platform",
    description="PUF-based Multifactor Authentication for Banking & IoT",
    version="0.3.0",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(ws.router, tags=["WebSocket"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.on_event("startup")
def on_startup() -> None:
    validate_security_settings(settings)
    init_db()
    load_or_generate_keypair(settings.rsa_private_key_path)


@app.get("/")
def root() -> dict:
    return {
        "name": "SecureVault Bank API",
        "phase": "3-puf-integrated",
        "docs": "/docs",
        "websocket": "/ws/auth",
        "environment": settings.app_env,
    }
