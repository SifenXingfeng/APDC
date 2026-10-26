param([string]$Profile='D:/APDC_PerformanceQA_20261023',[int]$MaxSeconds=240)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'test_process_cleanup.ps1')
# The game runs on a private desktop, without switching the input desktop.
# Explicit handle-based termination and exact-child log-viewer cleanup follow.
Add-Type -TypeDefinition @'
using System;using System.Text;using System.Runtime.InteropServices;
public static class APDCPerformanceRun {
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct SI {
  public int cb;public string reserved,desktop,title;public uint x,y,w,h,xc,yc,fill,flags;
  public short show,reserved2;public IntPtr reservedPtr,input,output,error;
 }
 [StructLayout(LayoutKind.Sequential)] public struct PI {public IntPtr process,thread;public uint pid,tid;}
 [StructLayout(LayoutKind.Sequential)] public struct BASIC {public long processTime,jobTime;public uint flags;public UIntPtr minWorking,maxWorking;public uint active;public UIntPtr affinity;public uint priority,scheduling;}
 [StructLayout(LayoutKind.Sequential)] public struct IO {public ulong readOps,writeOps,otherOps,readBytes,writeBytes,otherBytes;}
 [StructLayout(LayoutKind.Sequential)] public struct EXT {public BASIC basic;public IO io;public UIntPtr processMemory,jobMemory,peakProcess,peakJob;}
 [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern IntPtr CreateDesktop(string n,IntPtr d,IntPtr m,uint f,uint access,IntPtr sa);
 [DllImport("user32.dll")] public static extern bool CloseDesktop(IntPtr h);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr psa,IntPtr tsa,bool inherit,uint flags,IntPtr env,string cwd,ref SI si,out PI pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] public static extern IntPtr CreateJobObject(IntPtr sa,string name);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetInformationJobObject(IntPtr h,int cls,ref EXT info,uint size);
 [DllImport("kernel32.dll",SetLastError=true)] public static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32.dll")] public static extern uint ResumeThread(IntPtr thread);
 [DllImport("kernel32.dll")] public static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32.dll")] public static extern uint WaitForSingleObject(IntPtr handle,uint ms);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
}
'@
$testExe='D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
if (Get-Process -Name hoi4 -ErrorAction SilentlyContinue) { throw 'A game is already running; no test was started.' }
$testPreviousSteamState=Get-ItemProperty -LiteralPath 'HKCU:/Software/Valve/Steam/Apps/394360' -ErrorAction SilentlyContinue
if ($testPreviousSteamState.Running -eq 1) {throw 'Steam still marks HOI4 as running. Resolve the existing game/test helpers before starting another test.'}
$env:SteamAppId='394360';$env:SteamGameId='394360'
$testDesktopName='APDC_PerformanceQA_'+(Get-Date -Format 'yyyyMMdd_HHmmss')
$testDesktop=[APDCPerformanceRun]::CreateDesktop($testDesktopName,[IntPtr]::Zero,[IntPtr]::Zero,0,0x01FF,[IntPtr]::Zero)
if ($testDesktop -eq [IntPtr]::Zero) { throw 'Private desktop creation failed.' }
$testJob=[APDCPerformanceRun]::CreateJobObject([IntPtr]::Zero,$null)
$testLimits=New-Object APDCPerformanceRun+EXT;$testLimits.basic.flags=0x2008;$testLimits.basic.active=1
if (-not [APDCPerformanceRun]::SetInformationJobObject($testJob,9,[ref]$testLimits,[Runtime.InteropServices.Marshal]::SizeOf($testLimits))) { throw 'Job configuration failed.' }
$testSi=New-Object APDCPerformanceRun+SI;$testSi.cb=[Runtime.InteropServices.Marshal]::SizeOf($testSi)
$testSi.desktop='WinSta0\'+$testDesktopName;$testSi.flags=1;$testSi.show=0
$testPi=New-Object APDCPerformanceRun+PI
$testCommand=New-Object Text.StringBuilder ('"'+$testExe+'" -userdir='+$Profile+' -start_tag=GER -start_speed=3 -gamelog -debug')
try {
 if (-not [APDCPerformanceRun]::CreateProcess($testExe,$testCommand,[IntPtr]::Zero,[IntPtr]::Zero,$false,0x0204,[IntPtr]::Zero,(Split-Path $testExe),[ref]$testSi,[ref]$testPi)) { throw 'Private game launch failed.' }
 if (-not [APDCPerformanceRun]::AssignProcessToJobObject($testJob,$testPi.process)) { [APDCPerformanceRun]::TerminateProcess($testPi.process,1)|Out-Null;throw 'The game could not be contained in its cleanup job.' }
 $testRecord=@{pid=$testPi.pid;path=$testExe;profile=$Profile;desktop=$testDesktopName;started=(Get-Date).ToString('o');command=$testCommand.ToString();input_desktop_switched=$false;job_kill_on_close=$true;debug_mode=$true}
 $testRecord|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $Profile 'silent-process.json') -Encoding utf8
 [APDCPerformanceRun]::ResumeThread($testPi.thread)|Out-Null
 $testDeadline=(Get-Date).AddSeconds($MaxSeconds)
 while ((Get-Date) -lt $testDeadline -and [APDCPerformanceRun]::WaitForSingleObject($testPi.process,500) -eq 258) { }
} finally {
 if ($testPi.process -ne [IntPtr]::Zero -and [APDCPerformanceRun]::WaitForSingleObject($testPi.process,0) -eq 258) {
  [APDCPerformanceRun]::TerminateProcess($testPi.process,0)|Out-Null
 }
 [APDCPerformanceRun]::CloseHandle($testJob)|Out-Null
 if ($testPi.process -ne [IntPtr]::Zero) { [APDCPerformanceRun]::WaitForSingleObject($testPi.process,10000)|Out-Null;[APDCPerformanceRun]::CloseHandle($testPi.process)|Out-Null }
 if ($testPi.thread -ne [IntPtr]::Zero) { [APDCPerformanceRun]::CloseHandle($testPi.thread)|Out-Null }
 # Store Notepad can reparent/relaunch itself with a base64 session argument.
 # Parent PID alone misses those descendants. Match this exact profile and
 # launch interval, and include the game's own crash reporter.
 $testHelpers=@{closed_helper_pids=@();remaining_helper_pids=@()}
 if ($testRecord) {$testHelpers=Stop-APDCTestHelpers -Profile $Profile -Started ([datetime]$testRecord.started) -GameDirectory (Split-Path $testExe)}
 [APDCPerformanceRun]::CloseDesktop($testDesktop)|Out-Null
 for ($testShutdownPoll=0;$testShutdownPoll -lt 20;$testShutdownPoll++) {
  $testRemaining=Get-CimInstance Win32_Process -Filter ('ProcessId='+$testPi.pid)
  if (-not $testRemaining -or $testRemaining.ExecutablePath -ne $testExe -or -not $testRemaining.CommandLine.Contains($Profile)) { break }
  Start-Sleep -Milliseconds 500
 }
 for ($testSteamPoll=0;$testSteamPoll -lt 30;$testSteamPoll++) {
  $testSteamState=Get-ItemProperty -LiteralPath 'HKCU:/Software/Valve/Steam/Apps/394360' -ErrorAction SilentlyContinue
  if ($testSteamState.Running -ne 1) {break}
  Start-Sleep -Milliseconds 300
 }
 $testStop=@{stopped=(Get-Date).ToString('o');pid=$testPi.pid;closed_helpers=$testHelpers.closed_helper_pids;remaining_helpers=$testHelpers.remaining_helper_pids;still_running=[bool]$testRemaining;steam_app_running=($testSteamState.Running -eq 1)}
 $testStop|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $Profile 'silent-stop.json') -Encoding utf8
 if ($testStop.still_running -or $testHelpers.remaining_helper_pids.Count -gt 0 -or $testStop.steam_app_running) {throw 'Test cleanup is incomplete; inspect silent-stop.json. Do not report that all test processes exited.'}
}
