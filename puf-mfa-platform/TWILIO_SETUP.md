# WhatsApp OTP Setup (Twilio)

SecureVault Bank sends login OTPs via **Twilio WhatsApp**. Dev mode (OTP on screen) has been removed — you must configure Twilio.

---

## Step 1 — Create Twilio account

1. Go to [https://console.twilio.com](https://console.twilio.com)
2. Sign up (free trial gives ~$15 credit — enough for testing)
3. Verify your email and phone

---

## Step 2 — Join WhatsApp Sandbox

1. In Twilio Console → **Messaging** → **Try it out** → **Send a WhatsApp message**
2. You will see a sandbox number like `+1 415 523 8886`
3. On **your phone**, open WhatsApp and send the join code to that number:
   ```
   join <your-sandbox-code>
   ```
   Example: `join happy-tiger` (your code will be different)
4. You should get a reply: *"Your sandbox is ready"*

> Every phone number that receives OTP must join the sandbox first (during trial).

---

## Step 3 — Get API credentials

1. Twilio Console → **Account** → **Account Info**
2. Copy:
   - **Account SID** (starts with `AC...`)
   - **Auth Token** (click to reveal)

---

## Step 4 — Update backend `.env`

Edit `puf-mfa-platform/backend/.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

> Use the sandbox WhatsApp number shown in your Twilio console (usually `whatsapp:+14155238886`).

---

## Step 5 — Sign up with your real phone

1. Restart the backend after editing `.env`
2. Go to http://localhost:3000/signup
3. Use your **10-digit Indian mobile** (the same number you joined sandbox with):
   ```
   Phone: 9876543210
   ```
   (No +91 prefix in the form — app adds it automatically)

---

## Step 6 — Test login

1. Login with your account
2. After password, you should see: *"OTP sent to WhatsApp ending in XXXX"*
3. Check **WhatsApp** on your phone for the 6-digit code
4. Enter OTP → continue to PUF step if enabled

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Twilio WhatsApp is not configured" | Fill all 3 Twilio fields in `.env` and restart backend |
| OTP not received | Join sandbox from the same phone number used at signup |
| "WhatsApp OTP delivery failed" | Check Auth Token, sandbox join, and Twilio trial balance |
| Wrong country code | App sends to `+91` + your 10-digit number — use Indian format |
| 63016 error | Recipient has not joined the WhatsApp sandbox |

---

## Production (after trial)

For real users (not sandbox):

1. Apply for a **WhatsApp Business** sender in Twilio
2. Get Meta Business verification
3. Update `TWILIO_WHATSAPP_FROM` to your approved business number

For viva/demo, the **sandbox is sufficient**.
