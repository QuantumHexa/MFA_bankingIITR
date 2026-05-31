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

OTP is sent via **Twilio WhatsApp** only (no dev mode).

**Full setup guide:** [TWILIO_SETUP.md](./TWILIO_SETUP.md)

Quick steps:
1. Create Twilio account → join WhatsApp sandbox from your phone
2. Add credentials to `backend/.env`:
   ```env
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   ```
3. Restart backend · Sign up with your 10-digit phone (same number as sandbox)

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
