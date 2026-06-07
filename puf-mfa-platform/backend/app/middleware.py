import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = settings.content_security_policy
        if settings.cookie_secure or settings.is_production:
            response.headers["Strict-Transport-Security"] = f"max-age={settings.hsts_max_age}; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limit for auth endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self._rules = [
            ("/api/auth/login/start", 12, 60),
            ("/api/auth/login/verify-otp", 20, 60),
            ("/api/auth/login/verify-puf", 20, 60),
            ("/api/auth/signup", 8, 60),
            ("/api/auth/signup/puf-preview", 20, 60),
            ("/api/auth/login/resend-otp", 10, 60),
            ("/api/auth/refresh", 30, 60),
        ]
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        for prefix, max_requests, window in self._rules:
            if request.url.path.startswith(prefix):
                ip = request.client.host if request.client else "unknown"
                bucket = f"{prefix}:{ip}"
                now = time.time()
                self._hits[bucket] = [t for t in self._hits[bucket] if now - t < window]
                if len(self._hits[bucket]) >= max_requests:
                    return Response("Too many requests", status_code=429)
                self._hits[bucket].append(now)
                break
        return await call_next(request)
