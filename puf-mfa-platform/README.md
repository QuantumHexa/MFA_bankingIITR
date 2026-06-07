# SecureVault PUF-MFA Banking Platform

SecureVault is a full-stack banking security platform implementing three-factor authentication:

1. Password
2. WhatsApp OTP
3. PUF device verification (Virtual PUF or CMOD A7 hardware)

Repository: https://github.com/QuantumHexa/MFA_bankingIITR

## Tech Stack

- Frontend: Next.js 15, React, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: SQLite (dev), PostgreSQL-ready schema
- OTP: Twilio WhatsApp API
- PUF: Virtual TCP bridge or hardware serial bridge (CMOD A7)
- Security: Argon2 password hashing, OTP lockout/cooldown, JWT + refresh rotation, security headers

## Project Structure

```text
puf-mfa-platform/
  backend/        FastAPI APIs, auth logic, OTP, PUF verification
  frontend/       Next.js UI (login/signup/dashboard/admin)
  puf-bridge/     Virtual PUF server (and hardware integration path)
  deploy/         Reverse proxy config for production-style deployment
  docker-compose.yml
  start.ps1
```

## Authentication Flow

1. User logs in with username/email + password.
2. Backend sends OTP to registered WhatsApp number using Twilio.
3. User enters OTP (session-bound, expiry + lockout enforced).
4. If PUF is enabled, backend verifies challenge-response from registered device.
5. On success, access + refresh tokens are issued and session is completed.

## Quick Start (Windows)

```powershell
cd "d:\mfa banking project\puf-mfa-platform"
.\start.ps1
```

This starts:
- Virtual PUF bridge (`8765`)
- Backend API (`8000` by default if launched from script)
- Frontend (`3000`)

Open:
- App: http://localhost:3000
- API docs: http://127.0.0.1:8000/docs
- Admin: http://localhost:3000/admin

Default admin:
- Email: `admin@pufbank.dev`
- Password: `change-admin-password`

## Manual Start (3 terminals)

Terminal 1 (PUF bridge):
```powershell
cd "d:\mfa banking project\puf-mfa-platform\puf-bridge"
python virtual_puf_server.py
```

Terminal 2 (backend):
```powershell
cd "d:\mfa banking project\puf-mfa-platform\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 3 (frontend):
```powershell
cd "d:\mfa banking project\puf-mfa-platform\frontend"
npm run dev
```

## Twilio WhatsApp OTP Setup

1. Create Twilio account at https://console.twilio.com
2. Open Messaging -> Try WhatsApp -> Sandbox
3. Join sandbox from your phone by sending `join <sandbox-code>` to `+1 415 523 8886`
4. Update `backend/.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

5. Restart backend.
6. Sign up using your 10-digit phone number (same number that joined sandbox).

Notes:
- OTP is sent to `+91<phone>` format in current implementation.
- If Twilio is not configured, login OTP delivery will fail by design.

## PUF Modes

### Virtual PUF (default)
- Fastest for demo/testing.
- Uses TCP bridge at `127.0.0.1:8765`.

### Hardware PUF (CMOD A7)
Set in `backend/.env`:

```env
PUF_BRIDGE_MODE=hardware
HARDWARE_PUF_SERIAL_PORT=COM3
HARDWARE_PUF_BAUD=115200
PUF_HAMMING_THRESHOLD=5
```

Then restart backend.

## Security Features Implemented

- Argon2 password hashing with optional pepper
- OTP hashing (OTP never stored in plain text)
- OTP expiry, max attempts, lockout, resend cooldown and session send cap
- Refresh token rotation with hash storage and revocation
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, HSTS in secure/prod)
- Role-based access control (user/admin)
- Rate limiting middleware on sensitive paths
- Challenge-response based PUF verification with Hamming threshold

## Docker (Optional)

```bash
cd puf-mfa-platform
docker compose up --build
```

For production-style setup behind reverse proxy, use files in `deploy/`.

## Troubleshooting

- `EADDRINUSE` on `3000` or `8000`: stop old process using that port and restart.
- OTP not received: verify Twilio credentials + sandbox join + correct signup phone.
- PUF verification failed: ensure PUF bridge is running and user has enrolled PUF device.
- Login stuck on old behavior: clear old dev servers, restart backend/frontend cleanly.

## License / Academic Use

This project is built for cybersecurity demonstration and academic evaluation of multi-factor authentication with PUF integration.
