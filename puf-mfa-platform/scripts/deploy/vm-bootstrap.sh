#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Updating apt..."
sudo apt update
sudo apt install -y ca-certificates curl gnupg git

echo "[2/4] Installing Docker via official script..."
curl -fsSL https://get.docker.com | sh

echo "[3/4] Enabling current user for Docker group..."
sudo usermod -aG docker "$USER"

echo "[4/4] Done."
echo "Please logout/login (or reconnect SSH) before using docker without sudo."
