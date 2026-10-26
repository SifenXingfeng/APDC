param([string]$Profile='D:/APDC_EconomyQA_20261023')
$ErrorActionPreference='Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class APDCSilentWindowAudit {
 public delegate bool Callback(IntPtr hwnd,IntPtr lparam);
 [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] public static extern IntPtr OpenDesktop(string name,uint flags,bool inherit,uint access);
 [DllImport("user32.dll")] public static extern bool CloseDesktop(IntPtr handle);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Callback callback,IntPtr parameter);
 [DllImport("user32.dll")] public static extern bool EnumDesktopWindows(IntPtr desktop,Callback callback,IntPtr parameter);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid);
 public static int Count(uint target,IntPtr desktop) {
  int count=0; Callback callback=(hwnd,lp)=>{uint pid;GetWindowThreadProcessId(hwnd,out pid);if(pid==target)count++;return true;};
  if(desktop==IntPtr.Zero) EnumWindows(callback,IntPtr.Zero); else EnumDesktopWindows(desktop,callback,IntPtr.Zero);
  return count;
 }
}
'@
$econRecord=Get-Content -LiteralPath (Join-Path $Profile 'silent-process.json') -Raw | ConvertFrom-Json
$econProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+$econRecord.pid)
if (-not $econProcess -or $econProcess.ExecutablePath -ne $econRecord.path -or -not $econProcess.CommandLine.Contains($econRecord.profile)) {throw 'Test process identity does not match.'}
$econDesktop=[APDCSilentWindowAudit]::OpenDesktop($econRecord.desktop,0,$false,0x41)
if ($econDesktop -eq [IntPtr]::Zero) {throw 'Cannot inspect the private desktop.'}
try {
 $econAudit=@{pid=$econRecord.pid;private_desktop=$econRecord.desktop;windows_on_private_desktop=[APDCSilentWindowAudit]::Count($econRecord.pid,$econDesktop);windows_on_user_desktop=[APDCSilentWindowAudit]::Count($econRecord.pid,[IntPtr]::Zero);checked=(Get-Date).ToString('o');input_desktop_switched=$false}
 $econAudit | ConvertTo-Json | Set-Content -LiteralPath 'docs/economy/silent_verification.json' -Encoding utf8
 $econAudit | ConvertTo-Json
 if ($econAudit.windows_on_user_desktop -gt 0) {throw 'Test windows are on the user desktop.'}
} finally {[APDCSilentWindowAudit]::CloseDesktop($econDesktop) | Out-Null}
