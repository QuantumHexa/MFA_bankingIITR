# Free and Simple Deployment (Complete System)

This deploys the full stack (`frontend + backend + puf-bridge + postgres + reverse-proxy`) on one free Linux VM using Docker Compose.

## Recommended Free Host

- Oracle Cloud Always Free VM (best for full-stack + database).
- Any equivalent free VM also works.

## 1) Prepare a free domain

- Get a free domain/subdomain (for example DuckDNS).
- Point it to your VM public IP using an `A` record.
- Wait until DNS resolves.

## 2) Create VM and install Docker

Use Ubuntu 22.04/24.04 and run:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin git
sudo usermod -aG docker $USER
```

Log out and log in again once so `docker` works without `sudo`.

## 3) Upload project to the VM

```bash
git clone <your-repo-url>
cd puf-mfa-platform
```

## 4) Create production env file

```bash
cp .env.prod.example .env.prod
```

Edit `.env.prod` and set:

- `DOMAIN` to your real domain.
- `SECRET_KEY` to a strong random value.
- `POSTGRES_PASSWORD` to a strong password.
- `CORS_ORIGINS` to your real frontend domain.
- Twilio credentials if you want real WhatsApp OTP.

## 5) Open firewall ports

Allow:

- `80/tcp`
- `443/tcp`

## 6) Start the full system

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Check status:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

View logs:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f
```

## 7) Verify

- Open `https://<your-domain>`
- Admin login: configured admin email + password from `.env.prod` (currently default is `admin`)
- Backend docs: `https://<your-domain>/docs`

## Notes

- Caddy auto-issues TLS certificates for your domain.
- If your VM is stopped for long periods, users cannot access the app until it starts again.
- Twilio trial is not fully free forever; for long-term OTP delivery you will need a paid Twilio plan.
