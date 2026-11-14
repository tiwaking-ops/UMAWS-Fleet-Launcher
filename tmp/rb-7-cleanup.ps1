Set-Location 'C:\temp\projects\testproject1'

# List of clean worktrees to KEEP (unmerged branches)
$keep = @('T-0139-117', 'T-0148-120')

# Get all worktrees under work/ from git
$worktrees = git worktree list | ForEach-Object {
    $line = $_
    if ($line -match 'work\\([^\\s]+)\s+([a-f0-9]+)') {
        $name = $Matches[1]
        $path = "C:\temp\projects\testproject1\work\$name"
        @{ Name = $name; Path = $path }
    }
}

Write-Host "Found $($worktrees.Count) worktrees under work/"

foreach ($wt in $worktrees) {
    if ($keep -contains $wt.Name) {
        Write-Host "KEEP: $($wt.Name)"
    } else {
        Write-Host "REMOVING: $($wt.Name)"
        git worktree remove $wt.Path --force 2>&1
    }
}

Write-Host "Done removing work/ worktrees"

# Remove %TEMP%/pmk-merge-* trees
$mergeTrees = Get-ChildItem "$env:TEMP" -Filter "pmk-merge-*" -Directory -ErrorAction SilentlyContinue
if ($mergeTrees) {
    Write-Host "Found $($mergeTrees.Count) %TEMP%/pmk-merge-* trees"
    foreach ($mt in $mergeTrees) {
        Write-Host "REMOVING merge tree: $($mt.Name)"
        git worktree remove $mt.FullName --force 2>&1
    }
} else {
    Write-Host "No %TEMP%/pmk-merge-* trees found"
}

# Prune stale git worktree entries
Write-Host "Running git worktree prune..."
git worktree prune 2>&1

Write-Host "=== Final git worktree list ==="
git worktree list
