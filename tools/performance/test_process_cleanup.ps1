# Pure ownership matching, also covering Windows Store Notepad's encoded
# /SESSION command and the game's crash reporter after its parent exits.
function Test-APDCProcessOwnership {
 param([object]$Candidate,[string]$Profile,[datetime]$Started,[string]$GameDirectory)
 if (-not $Candidate.CreationDate -or $Candidate.CreationDate -lt $Started.AddSeconds(-1)) {return $false}
 $qaRoot=([IO.Path]::GetFullPath($Profile)).TrimEnd('\','/').Replace('/','\')
 $qaCommand=([string]$Candidate.CommandLine).Replace('/','\')
 if ($Candidate.Name -ieq 'CrashReporter.exe') {
  $qaExpected=Join-Path $GameDirectory 'crash_reporter\binaries\CrashReporter.exe'
  return ($Candidate.ExecutablePath -ieq $qaExpected -and $qaCommand.IndexOf($qaRoot+'\crashes\',[StringComparison]::OrdinalIgnoreCase) -ge 0)
 }
 if ($Candidate.Name -ine 'Notepad.exe') {return $false}
 $qaStrings=@([string]$Candidate.CommandLine)
 if ($Candidate.CommandLine -match '/SESSION:([A-Za-z0-9+/=]+)') {
  try {
   $qaPayload=[Convert]::FromBase64String($Matches[1])
   $qaStrings+=[Text.Encoding]::Unicode.GetString($qaPayload)
   if ($qaPayload.Length -gt 1) {$qaStrings+=[Text.Encoding]::Unicode.GetString($qaPayload,1,$qaPayload.Length-1)}
  } catch {return $false}
 }
 $qaLogPattern=[regex]::Escape($qaRoot+'\logs\')+'(?:error|game|system|setup|text|graphics|memory|performance)\.log(?=[\x00"\s]|$)'
 foreach ($qaString in $qaStrings) {
  if ([regex]::IsMatch($qaString.Replace('/','\'),$qaLogPattern,[Text.RegularExpressions.RegexOptions]::IgnoreCase)) {return $true}
 }
 return $false
}

function Stop-APDCTestHelpers {
 param([string]$Profile,[datetime]$Started,[string]$GameDirectory)
 $qaClosed=New-Object 'System.Collections.Generic.List[int]'
 $qaRemaining=@();$qaEmptyPolls=0
 for ($qaPass=0;$qaPass -lt 20;$qaPass++) {
  $qaRemaining=@(Get-CimInstance Win32_Process -Filter "Name='Notepad.exe' OR Name='CrashReporter.exe'" | Where-Object {Test-APDCProcessOwnership $_ $Profile $Started $GameDirectory})
  if ($qaRemaining.Count -eq 0) {
   $qaEmptyPolls++
   if ($qaEmptyPolls -ge 3) {break}
  } else {
   $qaEmptyPolls=0
   foreach ($qaCandidate in $qaRemaining) {
    # Recheck identity immediately before stopping a PID that could be reused.
    $qaCurrent=Get-CimInstance Win32_Process -Filter ('ProcessId='+$qaCandidate.ProcessId)
    if ($qaCurrent -and $qaCurrent.CreationDate -eq $qaCandidate.CreationDate -and $qaCurrent.ExecutablePath -eq $qaCandidate.ExecutablePath -and $qaCurrent.CommandLine -eq $qaCandidate.CommandLine -and (Test-APDCProcessOwnership $qaCurrent $Profile $Started $GameDirectory)) {
     Stop-Process -Id $qaCurrent.ProcessId -Force -ErrorAction Stop
     $qaClosed.Add([int]$qaCurrent.ProcessId)
    }
   }
  }
  Start-Sleep -Milliseconds 300
 }
 $qaRemaining=@(Get-CimInstance Win32_Process -Filter "Name='Notepad.exe' OR Name='CrashReporter.exe'" | Where-Object {Test-APDCProcessOwnership $_ $Profile $Started $GameDirectory})
 return @{closed_helper_pids=@($qaClosed.ToArray());remaining_helper_pids=@($qaRemaining | ForEach-Object {$_.ProcessId})}
}
