# SecureVault Bank — PUF-MFA Platform

Secure banking demo with **Password + WhatsApp OTP + PUF device** authentication.

## Quick Start

```powershell
cd puf-mfa-platform
.\start.ps1
```

| Service | URL |
|---------|-----|
| **App** | http://localhost:3000 |
| **API docs** | http://127.0.0.1:8000/docs |
| **Admin** | http://localhost:3000/admin |

**Admin:** `admin@pufbank.dev` / `change-admin-password`

---

## WhatsApp OTP

### Dev mode (default)
Twilio is **not required**. On login, the OTP appears **on screen** and in the backend terminal.

### Production (Twilio)
1. Create account at [Twilio Console](https://console.twilio.com)
2. Join **WhatsApp Sandbox** (Messaging → Try WhatsApp)
3. Add to `backend/.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

4. Restart backend. Sign up with 10-digit phone (e.g. `9876543210`).

---

## Hardware PUF (CMOD A7)

Set in `backend/.env`:

```env
PUF_BRIDGE_MODE=hardware
HARDWARE_PUF_SERIAL_PORT=COM3
HARDWARE_PUF_BAUD=115200
PUF_HAMMING_THRESHOLD=5
```

Check status in **Admin Panel → PUF Status**.

---

## Auth Flow

1. Sign up at `/signup` (enable PUF for 3-factor login)
2. Login → password → OTP → PUF verify
3. Dashboard — balance, security settings, live auth monitor
4. Admin — analytics, attack demos, export logs

---

## Docker

```bash
cd puf-mfa-platform
docker compose up --build
```

---

## GitHub

https://github.com/QuantumHexa/MFA_bankingIITR

See [ROADMAP.md](./ROADMAP.md) for phase checklist.
