@echo off
cd /d "%~dp0..\.."
echo Stopping SecureVault full stack...
docker compose --env-file .env.prod -f docker-compose.prod.yml down
echo.
echo Stopped. Data is preserved. Use start-local.cmd to start again.
pause
