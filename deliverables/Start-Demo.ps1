$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Python environment missing. Run: python -m venv .venv, then .\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt'
}
if (-not (Test-Path -LiteralPath 'backend\static\index.html')) {
    throw 'Frontend build missing. Run npm ci and npm run build from frontend first.'
}
$env:ENVIRONMENT = 'local'
$env:DATA_BACKEND = 'memory'
$env:AUTH_MODE = 'dev'
$env:DEV_AUTH_ENABLED = 'true'
$env:SEED_ENDPOINT_ENABLED = 'true'
$env:DEMO_DATA_MODE = 'true'
$env:GEMINI_ENABLED = 'false'
$env:SERVE_FRONTEND = 'true'
Write-Host 'TeamPulse AI demo: http://127.0.0.1:8000'
Write-Host 'Synthetic data and labelled AI fallback. Keep this terminal open. Ctrl+C stops the demo.'
Write-Host 'A new start resets the in-memory workspace.'
Set-Location (Join-Path $projectRoot 'backend')
& $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
