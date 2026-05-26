# Push to https://github.com/QuantumHexa/MFA_bankingIITR
$gh = "C:\Program Files\GitHub CLI\gh.exe"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "`n=== Step 1: Sign in to GitHub (one time) ===" -ForegroundColor Cyan
Write-Host "Browser will open. Sign in as QuantumHexa and approve.`n"
& $gh auth login --hostname github.com --git-protocol https --web

Write-Host "`n=== Step 2: Configure git to use GitHub CLI ===" -ForegroundColor Cyan
& $gh auth setup-git

Write-Host "`n=== Step 3: Connect remote ===" -ForegroundColor Cyan
git remote remove origin 2>$null
git remote add origin https://github.com/QuantumHexa/MFA_bankingIITR.git

Write-Host "`n=== Step 4: Commit (if needed) ===" -ForegroundColor Cyan
if (-not (git rev-parse HEAD 2>$null)) {
    git add .
    git commit -m "Initial commit: SecureVault PUF-MFA banking platform"
}

Write-Host "`n=== Step 5: Push to GitHub ===" -ForegroundColor Cyan
git branch -M main
git push -u origin main

Write-Host "`nDone! Repo: https://github.com/QuantumHexa/MFA_bankingIITR" -ForegroundColor Green
