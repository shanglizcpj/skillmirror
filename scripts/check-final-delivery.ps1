$ErrorActionPreference = "Continue"

$failed = 0
$warnings = 0

Write-Host ""
Write-Host "SkillMirror Final Delivery Check" -ForegroundColor Cyan
Write-Host "================================"

$projectRoot = Split-Path $PSScriptRoot -Parent

# 必须存在的交付文件
$requiredPaths = @(
    "frontend\src",
    "frontend\package.json",
    "frontend\Dockerfile",
    "frontend\nginx.conf",
    "frontend\.env.example",

    "backend\app",
    "backend\Dockerfile",
    "backend\requirements.txt",
    "backend\requirements.lock.txt",
    "backend\.env.example",

    "sandbox\Dockerfile",
    "sandbox\runner.py",

    "docker-compose.yml",
    ".gitignore",

    "scripts\verify-deployment.ps1"
)

Write-Host ""
Write-Host "1. Required files" -ForegroundColor Yellow

foreach ($relativePath in $requiredPaths) {
    $fullPath = Join-Path $projectRoot $relativePath

    if (Test-Path $fullPath) {
        Write-Host "[PASS] $relativePath" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Missing: $relativePath" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "2. Docker Compose validation" -ForegroundColor Yellow

Push-Location $projectRoot

docker compose config --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] docker-compose.yml is valid" `
        -ForegroundColor Green
}
else {
    Write-Host "[FAIL] docker-compose.yml is invalid" `
        -ForegroundColor Red
    $failed++
}

Pop-Location

Write-Host ""
Write-Host "3. B-side secret boundary" -ForegroundColor Yellow

$backendEnv = Join-Path $projectRoot "backend\.env"

if (Test-Path $backendEnv) {
    $forbiddenSecret = Select-String `
        -Path $backendEnv `
        -Pattern "SKILLMIRROR_A_EVIDENCE_SECRET" `
        -Quiet

    if ($forbiddenSecret) {
        Write-Host `
            "[FAIL] B .env contains SKILLMIRROR_A_EVIDENCE_SECRET" `
            -ForegroundColor Red

        Write-Host `
            "       Delete this variable from backend\.env immediately." `
            -ForegroundColor Red

        $failed++
    }
    else {
        Write-Host `
            "[PASS] A evidence secret is not stored by B" `
            -ForegroundColor Green
    }
}
else {
    Write-Host `
        "[WARN] backend\.env does not exist locally" `
        -ForegroundColor Yellow
    $warnings++
}

Write-Host ""
Write-Host "4. Files excluded from final package" `
    -ForegroundColor Yellow

$privatePaths = @(
    "backend\.env",
    "SkillMirror_A_Final_v2.1\.env",
    "backend\data\skillmirror_orchestrator.db",
    "frontend\node_modules",
    "frontend\dist",
    "backend\.venv",
    ".venv"
)

foreach ($relativePath in $privatePaths) {
    $fullPath = Join-Path $projectRoot $relativePath

    if (Test-Path $fullPath) {
        Write-Host `
            "[INFO] Local-only, do not package: $relativePath" `
            -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "5. Docker images" -ForegroundColor Yellow

$requiredImages = @(
    "skillmirror-backend:latest",
    "skillmirror-frontend:latest",
    "skillmirror-python-sandbox:latest"
)

$imageList = docker images --format "{{.Repository}}:{{.Tag}}"

foreach ($image in $requiredImages) {
    if ($imageList -contains $image) {
        Write-Host "[PASS] $image" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Missing image: $image" `
            -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "================================"

if ($failed -eq 0) {
    Write-Host "B15.1 DELIVERY CHECK PASSED" `
        -ForegroundColor Green

    if ($warnings -gt 0) {
        Write-Host "Warnings: $warnings" `
            -ForegroundColor Yellow
    }

    exit 0
}

Write-Host "B15.1 FAILED: $failed problem(s)" `
    -ForegroundColor Red

exit 1