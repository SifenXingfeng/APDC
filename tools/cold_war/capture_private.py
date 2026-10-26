"""Read-only PrintWindow capture of this QA's private desktop. Never switches input."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import json,sys
from PIL import Image

def run(profile):
    record=json.loads((profile/'silent-process.json').read_text('utf-8-sig'))
    u=C.WinDLL('user32',use_last_error=True);g=C.WinDLL('gdi32',use_last_error=True)
    u.OpenDesktopW.argtypes=[W.LPCWSTR,W.DWORD,W.BOOL,W.DWORD];u.OpenDesktopW.restype=W.HANDLE
    u.SetThreadDesktop.argtypes=[W.HANDLE];u.SetThreadDesktop.restype=W.BOOL
    u.CloseDesktop.argtypes=[W.HANDLE]
    cbtype=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    u.EnumDesktopWindows.argtypes=[W.HANDLE,cbtype,W.LPARAM]
    u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
    u.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
    u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
    u.GetDC.argtypes=[W.HWND];u.GetDC.restype=W.HDC
    u.PrintWindow.argtypes=[W.HWND,W.HDC,W.UINT];u.PrintWindow.restype=W.BOOL
    u.ReleaseDC.argtypes=[W.HWND,W.HDC]
    g.CreateCompatibleDC.argtypes=[W.HDC];g.CreateCompatibleDC.restype=W.HDC
    g.SelectObject.argtypes=[W.HDC,W.HGDIOBJ];g.SelectObject.restype=W.HGDIOBJ
    g.DeleteObject.argtypes=[W.HGDIOBJ];g.DeleteDC.argtypes=[W.HDC]
    class INFO(C.Structure):
        _fields_=[('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bitcount',W.WORD),('compression',W.DWORD),('image_size',W.DWORD),('xppm',W.LONG),('yppm',W.LONG),('colors',W.DWORD),('important',W.DWORD)]
    g.CreateDIBSection.argtypes=[W.HDC,C.POINTER(INFO),W.UINT,C.POINTER(C.c_void_p),W.HANDLE,W.DWORD];g.CreateDIBSection.restype=W.HBITMAP
    desktop=u.OpenDesktopW(record['desktop'],0,False,0x1ff)
    if not desktop:raise OSError(C.get_last_error())
    if not u.SetThreadDesktop(desktop):raise OSError(C.get_last_error())
    windows=[]
    @cbtype
    def collect(hwnd,param):
        pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));s=C.create_unicode_buffer(1024);u.GetWindowTextW(hwnd,s,1024)
        if pid.value==record['pid'] and 'Hearts of Iron' in s.value:windows.append(hwnd)
        return True
    u.EnumDesktopWindows(desktop,collect,0)
    if not windows:raise RuntimeError('Owned QA window not found')
    hwnd=windows[0];rect=W.RECT();u.GetClientRect(hwnd,C.byref(rect));w,h=rect.right,rect.bottom
    dc=u.GetDC(hwnd);mem=g.CreateCompatibleDC(dc);info=INFO(C.sizeof(INFO),w,-h,1,32,0,w*h*4,0,0,0,0);bits=C.c_void_p()
    bitmap=g.CreateDIBSection(dc,C.byref(info),0,C.byref(bits),None,0);previous=g.SelectObject(mem,bitmap)
    try:
        ok=u.PrintWindow(hwnd,mem,3)
        im=Image.frombytes('RGBA',(w,h),C.string_at(bits,w*h*4),'raw','BGRA').convert('RGB')
        out=profile/'private-window.png';im.save(out)
        report={'success':bool(ok),'size':[w,h],'image':str(out),'input_desktop_switched':False,'mouse_or_keyboard_sent':False,'distinct_colors':len(im.getcolors(w*h) or [])}
        (profile/'private-window.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report))
    finally:
        g.SelectObject(mem,previous);g.DeleteObject(bitmap);g.DeleteDC(mem);u.ReleaseDC(hwnd,dc);u.CloseDesktop(desktop)

if __name__=='__main__':run(Path(sys.argv[1]))
