@echo off
cd /d "%~dp0..\.."
echo Starting SecureVault full stack...
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
echo.
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
echo.
echo Open: https://localhost
pause
