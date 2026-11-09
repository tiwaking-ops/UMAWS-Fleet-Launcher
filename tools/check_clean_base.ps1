<#
.SYNOPSIS
    Run the PDD clean-base gate in a detached worktree at HEAD.

.DESCRIPTION
    Implements the Phase 5.2 proof from
    docs/plans/proposal-synthesized-umaws-fleet-launcher-repair-v1.md:

      1. resolve HEAD and add a detached worktree next to the repository;
      2. pin PYTHONPATH to that worktree and prove ``import cna`` / ``import pmk``
         resolve inside it (the original P-01 root cause was an editable install
         shadowing the worktree);
      3. run ``python -m pytest -q`` and capture the log;
      4. remove the worktree on success, keep it for inspection on failure;
      5. exit with the gate's exit code.

.PARAMETER RepoRoot
    Repository root. Defaults to the parent of this script's directory.

.PARAMETER Stamp
    Suffix for the gate worktree and log. Defaults to a local timestamp.

.PARAMETER Python
    Python executable. Defaults to ``python`` on PATH.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [string]$Stamp = (Get-Date -Format 'yyyyMMdd-HHmmss'),
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
}

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    throw "not a git worktree: $RepoRoot"
}

$origin = Get-Location
Push-Location $RepoRoot
try {
    $sha = (& git rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'git rev-parse HEAD failed' }

    $wt = Join-Path (Split-Path -Parent $RepoRoot) "umaws-gate-$Stamp"
    $log = Join-Path $RepoRoot "tmp\clean-base-$Stamp.log"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $log) | Out-Null

    & git worktree add --detach $wt $sha
    if ($LASTEXITCODE -ne 0) { throw 'git worktree add failed' }

    $gateExit = 1
    try {
        $env:PYTHONPATH = "$wt\src;$wt\tests"
        Push-Location $wt
        try {
            # cna is a namespace package without __init__.py, so cna.__file__
            # is None even when the worktree copy wins.  Import a real module
            # from each package and verify the file that actually loaded.
            $imports = & $Python -c 'import cna.engine.loop, pmk; print(cna.engine.loop.__file__); print(pmk.__file__)'
            if ($LASTEXITCODE -ne 0) { throw 'import check failed' }
            $imports | ForEach-Object { Write-Host $_ }
            foreach ($line in $imports) {
                if ($line -notlike "$wt*") {
                    throw "import shadowing: cna/pmk resolved outside $wt"
                }
            }

            & $Python -m pytest -q *> $log
            $gateExit = $LASTEXITCODE
            Get-Content -Path $log -Tail 12 | Write-Host
        }
        finally {
            Pop-Location
        }
    }
    finally {
        $env:PYTHONPATH = $null
        if ($gateExit -eq 0) {
            & git worktree remove --force $wt
            & git worktree prune
        }
        else {
            Write-Host "gate worktree kept for inspection: $wt"
            Write-Host "gate log: $log"
        }
    }

    Write-Host "clean-base gate exit=$gateExit sha=$sha"
    exit $gateExit
}
finally {
    Pop-Location
    Set-Location $origin
}
