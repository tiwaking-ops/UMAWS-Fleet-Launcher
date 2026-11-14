Set-Location 'C:\temp\projects\testproject1'
$base = '0d25d38'
$wt = 'C:\temp\projects\clean-base-gate'
if (Test-Path $wt) { git worktree remove $wt --force 2>$null }
git worktree add $wt $base
Set-Location $wt
$env:PYTHONPATH = "C:\temp\projects\clean-base-gate\src"
python -c "import cna, pmk; print('cna:', cna.__file__); print('pmk:', pmk.__file__)"
python -m pytest -q > 'C:\temp\projects\testproject1\tmp\rb-5-clean-base-gate.log' 2>&1
echo EXIT_CODE=$LASTEXITCODE
