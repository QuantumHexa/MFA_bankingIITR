# Windows Detailed Deployment Guide (Free Options)

This project can be deployed in two free ways:

- **Option A (Recommended): Free Linux VM + Docker Compose**  
  Better for a real "always available" deployment.
- **Option B: Run on your Windows PC + Cloudflare Tunnel**  
  Easiest if you do not want VM setup, but your PC must stay ON.

---

## Before You Start (Windows)

Install these on Windows:

1. Git for Windows: [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Docker Desktop: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
3. PowerShell 7+ (optional but recommended): [https://learn.microsoft.com/powershell/](https://learn.microsoft.com/powershell/)

Verify in PowerShell:

```powershell
git --version
docker --version
docker compose version
```

---

## Option A (Recommended): Free VM Deployment

Use this when you want public deployment that is more stable than running on your own PC.

### A1) Create VM and network access

1. Create Ubuntu VM (Oracle Cloud Always Free).
2. Open inbound ports on security list / firewall:
   - `22` (SSH)
   - `80` (HTTP)
   - `443` (HTTPS)
3. Reserve static public IP if available.

### A2) Point domain to VM

1. Create a free domain/subdomain (DuckDNS works well).
2. Add `A` record to VM public IP.
3. Wait for DNS propagation.

### A3) Prepare project for production (on Windows)

In PowerShell:

```powershell
cd "d:\mfa banking project\puf-mfa-platform"
powershell -ExecutionPolicy Bypass -File ".\scripts\deploy\prepare-env-prod.ps1"
```

This creates `.env.prod` from `.env.prod.example` and asks for key values.

### A4) Connect to VM from Windows

```powershell
ssh -i "C:\path\to\oracle-key.key" ubuntu@<VM_PUBLIC_IP>
```

### A5) Install Docker on VM

Copy/paste this in VM terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/docker/docker-install/master/install.sh | sh
sudo usermod -aG docker $USER
exit
```

Reconnect SSH and test:

```bash
docker --version
docker compose version
```

### A6) Upload code to VM

**Simplest:** push to GitHub from Windows, then clone on VM.

On Windows:

```powershell
cd "d:\mfa banking project\puf-mfa-platform"
git add .
git commit -m "prepare prod deploy"
git push
```

On VM:

```bash
git clone <your-repo-url>
cd puf-mfa-platform
```

### A7) Start full stack on VM

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

### A8) Verify

- `https://<your-domain>`
- `https://<your-domain>/docs`

---

## Option B: Windows PC + Cloudflare Tunnel (No VM)

Use this when you want easiest setup and zero VM work.

### B1) Start app locally in Docker

In PowerShell:

```powershell
cd "d:\mfa banking project\puf-mfa-platform"
powershell -ExecutionPolicy Bypass -File ".\scripts\deploy\prepare-env-prod.ps1"
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

### B2) Create free Cloudflare Tunnel

1. Create Cloudflare account and add your domain.
2. Install `cloudflared` on Windows:
   [https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
3. Login:

```powershell
cloudflared tunnel login
```

4. Create tunnel:

```powershell
cloudflared tunnel create puf-mfa
```

5. Route DNS:

```powershell
cloudflared tunnel route dns puf-mfa app.yourdomain.com
```

6. Run tunnel to your local reverse proxy:

```powershell
cloudflared tunnel run --url http://localhost:80 puf-mfa
```

Now your app is reachable on `https://app.yourdomain.com`.

---

## Which Option Should You Choose?

- Choose **Option A (VM)** if you want proper deployment and better uptime.
- Choose **Option B (Cloudflare Tunnel)** if you want fastest setup from Windows.

---

## Known Limits of "Free"

- Twilio WhatsApp OTP is trial-limited, not permanently free.
- Free VMs may have performance or quota limits.
- Option B requires your Windows machine to stay online.
