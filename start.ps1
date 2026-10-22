# start.ps1 — start the UMAWS Fleet Console and open the browser.
#
# Double-click start.cmd (which calls this file), or run it from
# PowerShell:
#
#     .\start.ps1
#
# The Console binds to 127.0.0.1 only.  It has no authentication, because
# the operator asked for no restrictions, but a LAN-exposed control surface
# is not "no restrictions", it is an open door — so the bind address is not
# configurable from the browser.

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$RepoRoot = $PSScriptRoot
$Port = 8765

# --- locate the interpreter -------------------------------------------------
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "No virtual environment found at $Python" -ForegroundColor Red
    Write-Host "Create it with:  py -3.12 -m venv .venv" -ForegroundColor Yellow
    Write-Host "then:           .\.venv\Scripts\python.exe -m pip install -e . --no-deps" -ForegroundColor Yellow
    exit 1
}

# --- environment ------------------------------------------------------------
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# --- start ------------------------------------------------------------------
$Url = "http://127.0.0.1:$Port"
Write-Host "UMAWS Fleet Console" -ForegroundColor Cyan
Write-Host "  repository : $RepoRoot"
Write-Host "  console    : $Url"
Write-Host "  stop       : Ctrl+C in this window, or close it" -ForegroundColor DarkGray
Write-Host ""

# Open the browser once the server is listening.
Start-Job -Name "umaws-open-browser" -ScriptBlock {
    param($Url)
    for ($i = 0; $i -lt 40; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            Start-Process $Url
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
} -ArgumentList $Url | Out-Null

& $Python -m console.app --root $RepoRoot --port $Port
