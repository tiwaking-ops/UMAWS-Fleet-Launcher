Set-Location 'C:\temp\projects\testproject1'
$result = python -m pytest -q --collect-only tests/fleet tests/pmk 2>&1
Write-Host "EXIT_CODE=$LASTEXITCODE"
$result | Select-Object -Last 3
