import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limit for auth endpoints."""

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/auth/login") or request.url.path.startswith("/api/auth/signup"):
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            self._hits[ip] = [t for t in self._hits[ip] if now - t < self.window]
            if len(self._hits[ip]) >= self.max_requests:
                return Response("Too many requests", status_code=429)
            self._hits[ip].append(now)
        return await call_next(request)
