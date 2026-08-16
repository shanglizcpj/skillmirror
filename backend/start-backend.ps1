$ErrorActionPreference = "Stop"

$BackendDirectory = Split-Path `
    -Parent $MyInvocation.MyCommand.Path

Set-Location $BackendDirectory

Write-Host ""
Write-Host "========================================"
Write-Host " SkillMirror B Backend"
Write-Host "========================================"
Write-Host ""

$EnvironmentFile = Join-Path `
    $BackendDirectory ".env"

if (-not (Test-Path $EnvironmentFile)) {
    throw @"
Missing backend/.env file.

Create it with:
Copy-Item .env.example .env

Then replace the Token and Secret placeholders.
"@
}

foreach ($Line in Get-Content $EnvironmentFile) {
    $TrimmedLine = $Line.Trim()

    if (
        -not $TrimmedLine -or
        $TrimmedLine.StartsWith("#")
    ) {
        continue
    }

    $Parts = $TrimmedLine -split "=", 2

    if ($Parts.Count -ne 2) {
        continue
    }

    $Name = $Parts[0].Trim()
    $Value = $Parts[1].Trim()

    [Environment]::SetEnvironmentVariable(
        $Name,
        $Value,
        "Process"
    )
}

$RequiredVariables = @(
    "SKILLMIRROR_A_BASE_URL",
    "SKILLMIRROR_INTERNAL_TOKEN",
    "SKILLMIRROR_B_PROVENANCE_SECRET"
)

foreach ($VariableName in $RequiredVariables) {
    $Value = [Environment]::GetEnvironmentVariable(
        $VariableName,
        "Process"
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing environment variable: $VariableName"
    }

    if ($Value.StartsWith("replace-with-")) {
        throw @"
$VariableName still contains the example placeholder.
Please edit backend/.env and insert the real shared value.
"@
    }
}

$PythonExecutable = Join-Path `
    $BackendDirectory ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExecutable)) {
    throw @"
Python virtual environment was not found.

Create it with:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
"@
}

Write-Host "A service:"
Write-Host $env:SKILLMIRROR_A_BASE_URL

Write-Host ""
Write-Host "B backend:"
Write-Host "http://127.0.0.1:8001"

Write-Host ""
Write-Host "OpenAPI:"
Write-Host "http://127.0.0.1:8001/docs"

Write-Host ""
Write-Host "Press Ctrl+C to stop."
Write-Host ""

& $PythonExecutable `
    -m uvicorn `
    app.main:app `
    --host 127.0.0.1 `
    --port 8001 `
    --reload