"""Resize only the recorded QA window on its private desktop; no user input."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import sys


def run(profile):
    record=json.loads((profile/'silent-process.json').read_text('utf-8-sig'))
    assert record['desktop'].startswith('APDC_PerformanceQA_')
    assert Path(record['profile']).resolve()==profile.resolve()
    u=C.WinDLL('user32',use_last_error=True);k=C.WinDLL('kernel32',use_last_error=True)
    u.SetProcessDPIAware()
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
    k.CloseHandle.argtypes=[W.HANDLE]
    process=k.OpenProcess(0x1000,False,record['pid']);assert process
    path=C.create_unicode_buffer(32768);length=W.DWORD(len(path))
    try:
        assert k.QueryFullProcessImageNameW(process,0,path,C.byref(length))
        assert Path(path.value).resolve()==Path(record['path']).resolve()
    finally:k.CloseHandle(process)
    u.OpenDesktopW.argtypes=[W.LPCWSTR,W.DWORD,W.BOOL,W.DWORD];u.OpenDesktopW.restype=W.HANDLE
    u.SetThreadDesktop.argtypes=[W.HANDLE];u.CloseDesktop.argtypes=[W.HANDLE]
    desktop=u.OpenDesktopW(record['desktop'],0,False,0x1ff);assert desktop
    assert u.SetThreadDesktop(desktop)
    callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    u.EnumDesktopWindows.argtypes=[W.HANDLE,callback,W.LPARAM]
    u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
    u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    windows=[]
    @callback
    def collect(hwnd,_):
        pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid))
        r=W.RECT();u.GetClientRect(hwnd,C.byref(r))
        if pid.value==record['pid'] and r.right>=1200 and r.bottom>=700:windows.append(hwnd)
        return True
    try:
        u.EnumDesktopWindows(desktop,collect,0);assert len(windows)==1,windows
        hwnd=windows[0];client=W.RECT();outer=W.RECT()
        u.GetClientRect(hwnd,C.byref(client));u.GetWindowRect(hwnd,C.byref(outer))
        before=[client.right,client.bottom]
        width=1920+(outer.right-outer.left-client.right)
        height=1080+(outer.bottom-outer.top-client.bottom)
        # NOMOVE | NOZORDER | NOACTIVATE. No SwitchDesktop, focus or input.
        assert u.SetWindowPos(hwnd,None,0,0,width,height,0x2|0x4|0x10)
        u.GetClientRect(hwnd,C.byref(client))
        result={'pid':record['pid'],'before':before,'after':[client.right,client.bottom],'input_desktop_switched':False,'mouse_or_keyboard_sent':False}
        (profile/'private-resize.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result))
    finally:u.CloseDesktop(desktop)


if __name__=='__main__':run(Path(sys.argv[1]))
