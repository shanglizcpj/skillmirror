$ErrorActionPreference = "Continue"

$failed = 0
$warnings = 0

$projectRoot = Split-Path $PSScriptRoot -Parent
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"

function Test-Url {
    param(
        [string]$Name,
        [string]$Url,
        [int]$Attempts = 10
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest `
                -Uri $Url `
                -UseBasicParsing `
                -TimeoutSec 5

            if ($response.StatusCode -eq 200) {
                Write-Host "[PASS] $Name -> $Url" `
                    -ForegroundColor Green
                return $true
            }
        }
        catch {
            if ($attempt -lt $Attempts) {
                Start-Sleep -Seconds 3
            }
        }
    }

    Write-Host "[FAIL] $Name -> $Url" `
        -ForegroundColor Red

    return $false
}

Write-Host ""
Write-Host "SkillMirror Final System Tests" `
    -ForegroundColor Cyan
Write-Host "=============================="

# 1. 后端语法检查
Write-Host ""
Write-Host "1. Backend Python compilation" `
    -ForegroundColor Yellow

$backendPython = Join-Path `
    $backendRoot `
    ".venv\Scripts\python.exe"

if (Test-Path $backendPython) {
    Push-Location $backendRoot

    & $backendPython -m compileall -q app

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[PASS] Backend compilation" `
            -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Backend compilation" `
            -ForegroundColor Red
        $failed++
    }

    Pop-Location
}
else {
    Write-Host "[FAIL] Backend virtual environment not found" `
        -ForegroundColor Red
    Write-Host "       Expected: backend\.venv"
    $failed++
}

# 2. 前端生产构建
Write-Host ""
Write-Host "2. Frontend production build" `
    -ForegroundColor Yellow

Push-Location $frontendRoot

npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] Frontend production build" `
        -ForegroundColor Green
}
else {
    Write-Host "[FAIL] Frontend production build" `
        -ForegroundColor Red
    $failed++
}

Pop-Location

# 3. Docker Compose配置
Write-Host ""
Write-Host "3. Docker Compose validation" `
    -ForegroundColor Yellow

Push-Location $projectRoot

docker compose config --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] Docker Compose configuration" `
        -ForegroundColor Green
}
else {
    Write-Host "[FAIL] Docker Compose configuration" `
        -ForegroundColor Red
    $failed++
}

# 4. 启动容器
Write-Host ""
Write-Host "4. Starting Docker services" `
    -ForegroundColor Yellow

docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "[PASS] Docker Compose started" `
        -ForegroundColor Green
}
else {
    Write-Host "[FAIL] Docker Compose startup" `
        -ForegroundColor Red
    $failed++
}

docker compose ps

Pop-Location

# 5. 服务健康检查
Write-Host ""
Write-Host "5. Service health checks" `
    -ForegroundColor Yellow

if (-not (Test-Url `
    -Name "A service" `
    -Url "http://127.0.0.1:8000/health")) {
    $failed++
}

if (-not (Test-Url `
    -Name "B backend" `
    -Url "http://127.0.0.1:8001/health")) {
    $failed++
}

if (-not (Test-Url `
    -Name "B OpenAPI" `
    -Url "http://127.0.0.1:8001/docs")) {
    $failed++
}

if (-not (Test-Url `
    -Name "Production frontend" `
    -Url "http://127.0.0.1:8080/health")) {
    $failed++
}

# 6. 数据库检查
Write-Host ""
Write-Host "6. Database check" `
    -ForegroundColor Yellow

$databasePath = Join-Path `
    $backendRoot `
    "data\skillmirror_orchestrator.db"

if (Test-Path $databasePath) {
    $databaseSize = (Get-Item $databasePath).Length

    Write-Host "[PASS] Database exists" `
        -ForegroundColor Green
    Write-Host "       Size: $databaseSize bytes"
}
else {
    Write-Host "[FAIL] Database not found" `
        -ForegroundColor Red
    $failed++
}

# 最终结果
Write-Host ""
Write-Host "=============================="

if ($failed -eq 0) {
    Write-Host "B15.2 AUTOMATED TESTS PASSED" `
        -ForegroundColor Green

    Write-Host ""
    Write-Host "Continue with the browser test:"
    Write-Host "http://127.0.0.1:8080"

    exit 0
}

Write-Host "B15.2 FAILED: $failed test(s) failed" `
    -ForegroundColor Red

Write-Host ""
Write-Host "Diagnostics:"
Write-Host "docker compose ps"
Write-Host "docker compose logs backend --tail=100"
Write-Host "docker compose logs frontend --tail=100"

exit 1