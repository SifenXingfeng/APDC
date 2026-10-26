param([Parameter(Mandatory=$true)][string]$Profile)
$ErrorActionPreference='Stop'
$testRecord=Get-Content -LiteralPath (Join-Path $Profile 'silent-process.json') -Raw | ConvertFrom-Json
$testProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+$testRecord.pid)
if ($testProcess) {
    if ($testProcess.ExecutablePath -ne $testRecord.path -or -not $testProcess.CommandLine.Contains($testRecord.profile)) {
        throw 'Process identity differs from this QA record; no process was stopped.'
    }
    Stop-Process -Id $testRecord.pid -Force
    Wait-Process -Id $testRecord.pid -Timeout 20 -ErrorAction SilentlyContinue
}
# launch_silent.ps1 owns the desktop/job and performs helper and Steam cleanup.
