$procs = Get-Process python* -ErrorAction SilentlyContinue
if ($procs) {
    foreach ($p in $procs) {
        $cpu = $p.CPU
        $mem = [math]::round($p.WorkingSet64/1MB)
        Write-Host "PID: $($p.Id) CPU: $cpu s Mem: $mem MB"
    }
} else {
    Write-Host "No python processes found"
}