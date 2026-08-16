$ErrorActionPreference = "Continue"

$failed = 0

function Test-Service {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UseBasicParsing `
            -TimeoutSec 5

        if ($response.StatusCode -eq 200) {
            Write-Host "[PASS] $Name -> $Url" -ForegroundColor Green
        }
        else {
            Write-Host "[FAIL] $Name returned $($response.StatusCode)" `
                -ForegroundColor Red
            $script:failed++
        }
    }
    catch {
        Write-Host "[FAIL] $Name -> $Url" -ForegroundColor Red
        Write-Host "       $($_.Exception.Message)" -ForegroundColor DarkRed
        $script:failed++
    }
}

Write-Host ""
Write-Host "SkillMirror B14 Deployment Verification" `
    -ForegroundColor Cyan
Write-Host "======================================="

Write-Host ""
Write-Host "1. Checking Docker containers..." `
    -ForegroundColor Yellow

docker compose ps

if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] docker compose is unavailable" `
        -ForegroundColor Red
    $failed++
}
else {
    Write-Host "[PASS] docker compose is available" `
        -ForegroundColor Green
}

Write-Host ""
Write-Host "2. Checking Docker images..." `
    -ForegroundColor Yellow

$requiredImages = @(
    "skillmirror-backend:latest",
    "skillmirror-frontend:latest",
    "skillmirror-python-sandbox:latest"
)

$imageList = docker images --format "{{.Repository}}:{{.Tag}}"

foreach ($image in $requiredImages) {
    if ($imageList -contains $image) {
        Write-Host "[PASS] Image: $image" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Missing image: $image" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "3. Checking services..." `
    -ForegroundColor Yellow

Test-Service `
    -Name "A service" `
    -Url "http://127.0.0.1:8000/health"

Test-Service `
    -Name "B backend" `
    -Url "http://127.0.0.1:8001/health"

Test-Service `
    -Name "Frontend" `
    -Url "http://127.0.0.1:8080/health"

Write-Host ""
Write-Host "4. Checking database persistence..." `
    -ForegroundColor Yellow

$databasePath = Join-Path `
    $PSScriptRoot `
    "..\backend\data\skillmirror_orchestrator.db"

$databasePath = [System.IO.Path]::GetFullPath($databasePath)

if (Test-Path $databasePath) {
    $databaseSize = (Get-Item $databasePath).Length

    Write-Host "[PASS] Database exists" -ForegroundColor Green
    Write-Host "       $databasePath"
    Write-Host "       Size: $databaseSize bytes"
}
else {
    Write-Host "[FAIL] Database does not exist: $databasePath" `
        -ForegroundColor Red
    $failed++
}

Write-Host ""
Write-Host "======================================="

if ($failed -eq 0) {
    Write-Host "B14 DEPLOYMENT PASSED" `
        -ForegroundColor Green
    Write-Host "Open: http://127.0.0.1:8080"
    exit 0
}

Write-Host "B14 DEPLOYMENT FAILED: $failed check(s) failed" `
    -ForegroundColor Red

Write-Host ""
Write-Host "Run diagnostics:"
Write-Host "docker compose ps"
Write-Host "docker compose logs backend --tail=100"
Write-Host "docker compose logs frontend --tail=100"

exit 1