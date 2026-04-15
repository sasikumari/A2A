$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DocgenRoot = Join-Path $ProjectRoot "docgen"
$ProductBuilderRoot = Join-Path $ProjectRoot "product-builder"
$PbBackendDir = Join-Path $ProductBuilderRoot "backend"

function Write-Step($message) {
    Write-Host ""
    Write-Host $message -ForegroundColor Cyan
}

function Find-PythonLauncher {
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3") },
        @{ Cmd = "python"; Args = @() }
    )
    foreach ($candidate in $candidates) {
        try {
            & $candidate.Cmd @($candidate.Args + @("--version")) *> $null
            return $candidate
        } catch {
        }
    }
    throw "Python launcher not found. Install Python 3.10+ and ensure 'py' or 'python' is on PATH."
}

function Ensure-Venv {
    param(
        [string]$Directory,
        [string]$Label,
        [hashtable]$PyLauncher
    )

    $venvPath = Join-Path $Directory ".venv"
    $pythonExe = Join-Path $venvPath "Scripts\python.exe"

    if (-not (Test-Path $pythonExe)) {
        Write-Host "Creating virtual environment for $Label at $venvPath..."
        & $PyLauncher.Cmd @($PyLauncher.Args + @("-m", "venv", $venvPath))
    }

    return @{
        Venv = $venvPath
        Python = $pythonExe
    }
}

function Install-Requirements {
    param(
        [string]$PythonExe,
        [string]$RequirementsFile,
        [string]$Label
    )

    Write-Host "Installing $Label dependencies..."
    & $PythonExe -m pip install --disable-pip-version-check -r $RequirementsFile
}

function Wait-ForHttp200 {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    for ($i = 1; $i -le $TimeoutSeconds; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Host "Ready after ${i}s: $Url"
                return $true
            }
        } catch {
        }
        Start-Sleep -Seconds 1
    }

    Write-Warning "Service did not return HTTP 200 within $TimeoutSeconds seconds: $Url"
    return $false
}

$py = Find-PythonLauncher

Write-Host "================================================" -ForegroundColor Yellow
Write-Host " NPCI Hackathon Titans - Windows Launcher " -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Yellow
Write-Host "Project root: $ProjectRoot"

Write-Step "[1/4] Preparing embedded DocGen runtime..."
$docgenEnv = Ensure-Venv -Directory $DocgenRoot -Label "embedded DocGen" -PyLauncher $py
Install-Requirements -PythonExe $docgenEnv.Python -RequirementsFile (Join-Path $DocgenRoot "requirements.txt") -Label "DocGen"

Write-Step "[2/4] Preparing orchestrator runtime..."
$upiEnv = Ensure-Venv -Directory $ProjectRoot -Label "UPI orchestrator" -PyLauncher $py
Install-Requirements -PythonExe $upiEnv.Python -RequirementsFile (Join-Path $ProjectRoot "requirements.txt") -Label "root"

Write-Step "[3/4] Preparing frontend..."
Set-Location $ProductBuilderRoot
if (-not (Test-Path (Join-Path $ProductBuilderRoot "node_modules"))) {
    Write-Host "Installing npm dependencies..."
    & npm.cmd install
} else {
    Write-Host "node_modules found, skipping npm install."
}

$frontendLog = Join-Path $ProjectRoot "frontend.log"
$pbLog = Join-Path $ProjectRoot "pb_backend.log"

Write-Step "[4/4] Starting services..."

$frontendProc = Start-Process -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
    -WorkingDirectory $ProductBuilderRoot `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendLog `
    -PassThru

Write-Host "Frontend PID: $($frontendProc.Id)  (log: $frontendLog)"

$pbCommand = @"
`$env:PYTHONPATH = '$ProjectRoot'
Set-Location '$PbBackendDir'
& '$($docgenEnv.Python)' -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
"@

$pbProc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $pbCommand) `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $pbLog `
    -RedirectStandardError $pbLog `
    -PassThru

Write-Host "Product Builder backend PID: $($pbProc.Id)  (log: $pbLog)"

Write-Host ""
Write-Host "Waiting for Product Builder backend (port 8001)..."
[void](Wait-ForHttp200 -Url "http://localhost:8001/health" -TimeoutSeconds 30)

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host " Services starting up " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "Frontend:                http://127.0.0.1:5173"
Write-Host "Product Builder API:     http://localhost:8001"
Write-Host "UPI Orchestrator:        http://localhost:5000"
Write-Host ""
Write-Host "Logs:"
Write-Host "  Frontend:   $frontendLog"
Write-Host "  PB backend: $pbLog"
Write-Host ""
Write-Host "Optional standalone DocGen API:"
Write-Host "  & '$($docgenEnv.Python)' -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C in this window to stop the orchestrator. Frontend and PB backend continue until closed separately."
Write-Host ""

$env:PYTHONPATH = $ProjectRoot
Set-Location $ProjectRoot
& $upiEnv.Python -u "api\app.py"
