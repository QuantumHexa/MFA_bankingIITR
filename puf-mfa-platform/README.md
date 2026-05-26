# SecureVault Bank — PUF-MFA Platform

Secure banking demo with **Password + WhatsApp OTP + PUF device** authentication.

## Quick Start

```powershell
cd puf-mfa-platform
.\start.ps1
```

Or manually (3 terminals):

```powershell
# 1. PUF bridge
cd puf-bridge && python virtual_puf_server.py

# 2. Backend
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Frontend
cd frontend && npm run dev
```

| Service | URL |
|---------|-----|
| **App** | http://localhost:3000 |
| **API docs** | http://127.0.0.1:8000/docs |
| **WebSocket** | ws://127.0.0.1:8000/ws/auth |

**Admin:** `admin@pufbank.dev` / `change-admin-password`

In dev mode, WhatsApp OTP prints in the **backend terminal**.

## Auth Flow

1. Sign up at `/signup` (enable PUF for 3-factor login)
2. Login at `/login` → password → OTP → PUF verify
3. Dashboard shows balance, security settings, live auth monitor
4. Admin panel at `/admin` (admin users only)

## Phases

See [ROADMAP.md](./ROADMAP.md)
