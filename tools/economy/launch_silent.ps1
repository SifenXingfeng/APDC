param([string]$Profile='D:/APDC_EconomyQA_20261023')
$ErrorActionPreference='Stop'
# The game is created on a separate Windows desktop. This script never calls
# SwitchDesktop and cannot bring its game window onto the user's input desktop.
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class APDCSilentEconomyProcess {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
 public struct STARTUPINFO {
  public int cb; public string lpReserved,lpDesktop,lpTitle;
  public uint dwX,dwY,dwXSize,dwYSize,dwXCountChars,dwYCountChars,dwFillAttribute,dwFlags;
  public short wShowWindow,cbReserved2; public IntPtr lpReserved2,hStdInput,hStdOutput,hStdError;
 }
 [StructLayout(LayoutKind.Sequential)]
 public struct PROCESS_INFORMATION {public IntPtr hProcess,hThread;public uint dwProcessId,dwThreadId;}
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern IntPtr CreateDesktop(string n,IntPtr d,IntPtr m,uint f,uint a,IntPtr s);
 [DllImport("user32.dll", SetLastError=true)] public static extern bool CloseDesktop(IntPtr h);
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern bool CreateProcess(string a,StringBuilder c,IntPtr p,IntPtr t,bool inherit,uint flags,IntPtr env,string cwd,ref STARTUPINFO si,out PROCESS_INFORMATION pi);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetThreadDesktop(uint id);
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern bool GetUserObjectInformation(IntPtr h,int index,StringBuilder value,uint bytes,out uint needed);
 public static string DesktopName(uint thread) {
  var b=new StringBuilder(256);uint n;return GetUserObjectInformation(GetThreadDesktop(thread),2,b,512,out n)?b.ToString():"unavailable";
 }
}
'@
$econExe='D:\SteamLibrary\steamapps\common\Hearts of Iron IV\hoi4.exe'
# Child-only Steam application identity, as when launching this installed game.
$env:SteamAppId='394360'
$env:SteamGameId='394360'
$econDesktopName='APDC_EconomyQA_'+(Get-Date -Format 'yyyyMMdd_HHmmss')
$econDesktop=[APDCSilentEconomyProcess]::CreateDesktop($econDesktopName,[IntPtr]::Zero,[IntPtr]::Zero,0,0x01FF,[IntPtr]::Zero)
if ($econDesktop -eq [IntPtr]::Zero) { throw 'Unable to create the isolated desktop; game was not launched.' }
$econStartup=New-Object APDCSilentEconomyProcess+STARTUPINFO
$econStartup.cb=[Runtime.InteropServices.Marshal]::SizeOf($econStartup)
$econStartup.lpDesktop='WinSta0\'+$econDesktopName
$econStartup.dwFlags=1
$econStartup.wShowWindow=0
$econInfo=New-Object APDCSilentEconomyProcess+PROCESS_INFORMATION
$econCommand=New-Object Text.StringBuilder ('"'+$econExe+'" -userdir='+$Profile+' -start_tag=GER -start_speed=3 -gamelog -debug')
$econCreated=[APDCSilentEconomyProcess]::CreateProcess($econExe,$econCommand,[IntPtr]::Zero,[IntPtr]::Zero,$false,0x0200,[IntPtr]::Zero,(Split-Path $econExe),[ref]$econStartup,[ref]$econInfo)
if (-not $econCreated) {
 [APDCSilentEconomyProcess]::CloseDesktop($econDesktop) | Out-Null
 throw ('Silent launch failed: '+[Runtime.InteropServices.Marshal]::GetLastWin32Error())
}
$econRecord=@{pid=$econInfo.dwProcessId;thread=$econInfo.dwThreadId;path=$econExe;profile=$Profile;desktop=$econDesktopName;actual_desktop=[APDCSilentEconomyProcess]::DesktopName($econInfo.dwThreadId);started=(Get-Date).ToString('o');input_desktop_switched=$false}
$econRecord | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Profile 'silent-process.json') -Encoding utf8
[APDCSilentEconomyProcess]::CloseHandle($econInfo.hThread) | Out-Null
[APDCSilentEconomyProcess]::CloseHandle($econInfo.hProcess) | Out-Null
try {
 while (Get-Process -Id $econInfo.dwProcessId -ErrorAction SilentlyContinue) { Start-Sleep -Milliseconds 500 }
} finally {
 [APDCSilentEconomyProcess]::CloseDesktop($econDesktop) | Out-Null
}
