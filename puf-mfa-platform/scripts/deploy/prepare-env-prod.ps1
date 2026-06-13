param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
}

$template = Join-Path $ProjectRoot ".env.prod.example"
$target = Join-Path $ProjectRoot ".env.prod"

if (-not (Test-Path $template)) {
    throw "Template file not found: $template"
}

if (-not (Test-Path $target)) {
    Copy-Item $template $target
    Write-Host "Created $target from template."
}
else {
    Write-Host "$target already exists. Updating selected keys only."
}

$content = Get-Content $target -Raw

function Set-EnvValue {
    param(
        [string]$Text,
        [string]$Key,
        [string]$Value
    )

    $escaped = [Regex]::Escape($Key)
    $pattern = "(?m)^${escaped}=.*$"
    $replacement = "$Key=$Value"
    if ($Text -match $pattern) {
        return [Regex]::Replace($Text, $pattern, $replacement)
    }
    return ($Text.TrimEnd() + "`r`n" + $replacement + "`r`n")
}

$domain = Read-Host "Enter DOMAIN (example: app.yourdomain.com)"
if (-not [string]::IsNullOrWhiteSpace($domain)) {
    $content = Set-EnvValue -Text $content -Key "DOMAIN" -Value $domain
    $content = Set-EnvValue -Text $content -Key "CORS_ORIGINS" -Value "https://$domain"
    $content = Set-EnvValue -Text $content -Key "NEXT_PUBLIC_API_URL" -Value "https://$domain"
    $content = Set-EnvValue -Text $content -Key "NEXT_PUBLIC_WS_URL" -Value "wss://$domain/ws/auth"
}

$secret = Read-Host "Enter SECRET_KEY (leave empty to keep current)"
if (-not [string]::IsNullOrWhiteSpace($secret)) {
    $content = Set-EnvValue -Text $content -Key "SECRET_KEY" -Value $secret
}

$pgPassword = Read-Host "Enter POSTGRES_PASSWORD (leave empty to keep current)"
if (-not [string]::IsNullOrWhiteSpace($pgPassword)) {
    $content = Set-EnvValue -Text $content -Key "POSTGRES_PASSWORD" -Value $pgPassword
    $dbUserMatch = [Regex]::Match($content, "(?m)^POSTGRES_USER=(.*)$")
    $dbNameMatch = [Regex]::Match($content, "(?m)^POSTGRES_DB=(.*)$")
    $dbUser = if ($dbUserMatch.Success) { $dbUserMatch.Groups[1].Value } else { "pufmfa" }
    $dbName = if ($dbNameMatch.Success) { $dbNameMatch.Groups[1].Value } else { "puf_mfa" }
    $content = Set-EnvValue -Text $content -Key "DATABASE_URL" -Value "postgresql://$dbUser:$pgPassword@db:5432/$dbName"
}

$adminEmail = Read-Host "Enter ADMIN_EMAIL (leave empty to keep current)"
if (-not [string]::IsNullOrWhiteSpace($adminEmail)) {
    $content = Set-EnvValue -Text $content -Key "ADMIN_EMAIL" -Value $adminEmail
}

$adminPassword = Read-Host "Enter ADMIN_PASSWORD (leave empty to keep current)"
if (-not [string]::IsNullOrWhiteSpace($adminPassword)) {
    $content = Set-EnvValue -Text $content -Key "ADMIN_PASSWORD" -Value $adminPassword
}

$twilioSid = Read-Host "Enter TWILIO_ACCOUNT_SID (leave empty for now)"
if (-not [string]::IsNullOrWhiteSpace($twilioSid)) {
    $content = Set-EnvValue -Text $content -Key "TWILIO_ACCOUNT_SID" -Value $twilioSid
}

$twilioToken = Read-Host "Enter TWILIO_AUTH_TOKEN (leave empty for now)"
if (-not [string]::IsNullOrWhiteSpace($twilioToken)) {
    $content = Set-EnvValue -Text $content -Key "TWILIO_AUTH_TOKEN" -Value $twilioToken
}

$content | Set-Content $target -NoNewline

Write-Host ""
Write-Host "Done. Updated: $target"
Write-Host "Next:"
Write-Host "  docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build"
