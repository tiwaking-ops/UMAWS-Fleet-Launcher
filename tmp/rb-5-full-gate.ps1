Set-Location 'C:\temp\projects\testproject1'
$result = python -m pytest -q tests/fleet tests/pmk 2>&1
Write-Host "EXIT_CODE=$LASTEXITCODE"
$result | Select-Object -Last 10
