$ErrorActionPreference = "Stop"

$FrontendDirectory = Split-Path `
    -Parent $MyInvocation.MyCommand.Path

Set-Location $FrontendDirectory

Write-Host ""
Write-Host "========================================"
Write-Host " SkillMirror Frontend"
Write-Host "========================================"
Write-Host ""

$PackageFile = Join-Path `
    $FrontendDirectory "package.json"

if (-not (Test-Path $PackageFile)) {
    throw "frontend/package.json was not found."
}

$NodeModulesDirectory = Join-Path `
    $FrontendDirectory "node_modules"

if (-not (Test-Path $NodeModulesDirectory)) {
    Write-Host "Installing frontend dependencies..."

    & npm.cmd ci

    if ($LASTEXITCODE -ne 0) {
        throw "npm ci failed."
    }
}

Write-Host "Frontend:"
Write-Host "http://127.0.0.1:5173"

Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& npm.cmd run dev -- `
    --host 127.0.0.1 `
    --port 5173 `
    --strictPort