Set-Location 'C:\temp\projects\testproject1'
$files = @(
    'src/fleet/conductor.py',
    'src/fleet/dispatcher.py',
    'src/fleet/harness.py',
    'src/fleet/legacy.py',
    'src/fleet/merge.py',
    'src/fleet/project.py',
    'src/fleet/spawn.py',
    'src/pmk/events.py',
    'src/pmk/worktrees.py',
    'tests/fleet/test_adapter_paths.py',
    'tests/fleet/test_conductor_leases.py',
    'tests/fleet/test_fleet.py',
    'tests/fleet/test_regressions.py',
    'tests/pmk/test_worktree_lifecycle.py',
    'tests/test_subprocess_env_lint.py',
    'tools/check_subprocess_env.py'
)
foreach ($f in $files) {
    if (Test-Path $f) {
        $status = git status --short $f
        if ($status) { Write-Host "MODIFIED: $f" } else { Write-Host "CLEAN: $f" }
    } else {
        Write-Host "MISSING: $f"
    }
}
