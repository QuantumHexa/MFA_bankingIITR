# Connect this project to GitHub
# Run this script in PowerShell (it will open your browser to sign in)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "`n=== Step 1: Sign in to GitHub ===" -ForegroundColor Cyan
Write-Host "A browser window will open. Approve access, then return here.`n"
gh auth login --hostname github.com --git-protocol https --web

Write-Host "`n=== Step 2: Verify login ===" -ForegroundColor Cyan
gh auth status

Write-Host "`n=== Step 3: Initial commit (if needed) ===" -ForegroundColor Cyan
if (-not (git rev-parse HEAD 2>$null)) {
    git add .
    git commit -m "Initial commit: SecureVault PUF-MFA banking platform"
}

Write-Host "`n=== Step 4: Create GitHub repo & push ===" -ForegroundColor Cyan
$repoName = Read-Host "Enter repository name (e.g. puf-mfa-banking)"
$isPrivate = Read-Host "Private repo? (y/n)"

if ($isPrivate -eq "y") {
    gh repo create $repoName --private --source=. --remote=origin --push
} else {
    gh repo create $repoName --public --source=. --remote=origin --push
}

Write-Host "`nDone! Your code is on GitHub." -ForegroundColor Green
gh repo view --web
