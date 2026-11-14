$tempDir = "$env:TEMP"
$mergeTrees = Get-ChildItem $tempDir -Filter 'pmk-merge-*' -Directory -ErrorAction SilentlyContinue
Write-Host "Found $($mergeTrees.Count) pmk-merge-* trees"
foreach ($mt in $mergeTrees) {
    Write-Host "Removing: $($mt.FullName)"
    Remove-Item $mt.FullName -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path $mt.FullName) {
        Write-Host "  FAILED to remove"
    } else {
        Write-Host "  removed"
    }
}
Write-Host "Done"
