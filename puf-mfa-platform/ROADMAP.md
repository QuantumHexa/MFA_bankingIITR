# PUF-MFA Cybersecurity Platform — Phased Delivery Plan

Production-grade PUF-based Multifactor Authentication for banking & IoT security.

## Architecture Overview

```
[Next.js Frontend] <--REST/WebSocket--> [FastAPI Backend] <---> [PostgreSQL]
                                              |
                    +-------------------------+-------------------------+
                    |                         |                         |
            [WhatsApp OTP]            [PUF Bridge Service]      [Auth Event Bus]
            Twilio/Meta API           Virtual / Hardware UART
```

## Phase 1 — Foundation (Week 1)
- [x] Monorepo structure (`frontend`, `backend`, `puf-bridge`)
- [x] Environment templates & Docker Compose
- [x] Database schema (users, devices, sessions, auth_logs, nonces)
- [x] Shared API contract (OpenAPI)

**Deliverable:** Runnable skeleton, DB migrations, health checks.

## Phase 2 — Backend Core (Week 2)
- [x] FastAPI app with layered architecture (routes → services → repos)
- [x] User signup/login with bcrypt/Argon2
- [x] JWT access + refresh tokens
- [x] **WhatsApp OTP** (Twilio WhatsApp or Meta Cloud API)
- [x] **PUF toggle** per user (`puf_enabled` setting)
- [x] Nonce + timestamp validation (replay prevention)
- [x] WebSocket channel for live auth flow events
- [x] Admin API (users, logs, system stats)
- [x] Structured auth audit logs

**Deliverable:** Complete auth API tested via Swagger/Postman.

## Phase 3 — PUF Integration (Week 3)
- [x] Port `virtual_puf.py` into `puf-bridge` service
- [x] Hardware PUF adapter (CMOD A7 UART @ 115200, 16-byte C/R)
- [x] Enrollment: server challenge → device response → store reference + mask
- [x] Login: fresh challenge + fuzzy Hamming match for Arbiter PUF noise
- [x] User-selectable mode: Virtual PUF | Hardware PUF | PUF Off
- [x] Session key derivation (SHA-256/HMAC, lightweight crypto)

**Deliverable:** End-to-end PUF MFA with hardware OR virtual device.

## Phase 4 — Frontend UI/UX (Week 4–5)
- [x] Next.js 15 + TypeScript + Tailwind
- [x] Clean security-focused landing page
- [x] Signup / Login wired to backend API
- [x] User dashboard with PUF toggle & auth history
- [x] **Real-time auth flow visualization** (WebSocket stepper)
- [x] Admin panel (users, auth logs, stats)
- [x] Attack simulation demos (replay, clone, password-only bypass)
- [x] Recharts analytics charts
- [x] Dev OTP shown on login screen (no Twilio required)

**Deliverable:** Fully responsive web app connected to backend.

## Phase 5 — Security Hardening
- [x] Rate limiting on auth endpoints
- [x] Security headers
- [x] OTP expiry & single-use sessions
- [x] RBAC (user / admin)

## Phase 6 — Deployment (partial)
- [x] Docker multi-stage builds (backend + frontend + puf-bridge)
- [x] docker-compose
- [x] GitHub Actions CI
- [ ] Nginx + SSL production docs

## Current Status

**Platform feature-complete for demo/viva.** Optional: live CMOD A7 test, Twilio WhatsApp prod, Nginx deploy.


## Phase 6 — Deployment (Week 7)
- [ ] Docker multi-stage builds
- [ ] `docker-compose` (frontend, backend, db, puf-bridge)
- [ ] Nginx reverse proxy + SSL (Let's Encrypt)
- [ ] Production env docs
- [ ] GitHub Actions CI (lint, test, build)
- [ ] Optional: Vercel (frontend) + Railway/Render (backend)

**Deliverable:** One-command deploy README.

## Phase 7 — Portfolio Polish (Week 8)
- [ ] Demo video script & screenshots
- [ ] Architecture & sequence diagrams in UI
- [ ] IoT device simulator page
- [ ] Export auth logs (CSV)
- [ ] README with problem statement aligned to MFA_banking.pdf
- [ ] Viva/demo attack scenarios documented

---

## Feature Matrix (from PDF + version_8 + new)

| Feature | PDF | version_8 | New Web App |
|---------|-----|-----------|-------------|
| Password factor | ✓ | ✓ | ✓ |
| OTP factor | ✓ | SMS | **WhatsApp** |
| PUF factor | ✓ | ✓ | ✓ + toggle |
| Virtual PUF | — | ✓ | ✓ |
| Hardware PUF (CMOD A7) | ✓ | Serial | ✓ |
| Nonce/replay prevention | ✓ | partial | ✓ |
| Fresh challenge per login | ✓ | fixed | ✓ |
| Fuzzy PUF matching | ✓ | — | ✓ |
| Admin panel | — | basic | advanced |
| Real-time flow viz | — | — | ✓ |
| Attack demos | ✓ | — | ✓ |
| Dark/light mode | — | — | ✓ |

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui, Framer Motion, Recharts |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic v2 |
| Database | PostgreSQL (prod), SQLite (dev) |
| Real-time | WebSockets (FastAPI) |
| WhatsApp OTP | Twilio WhatsApp API (configurable) |
| PUF | Python bridge (virtual TCP + pyserial hardware) |
| Deploy | Docker, Nginx, GitHub Actions |

## Current Status

**Phase 4 integrated** — frontend connected to backend. Next: attack demos, hardware PUF, deployment.
