"""Send test mouse messages only to the recorded, owned private QA window."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import time


class PrivateWindow:
    def __init__(self,profile):
        self.profile=Path(profile);record=json.loads((self.profile/'silent-process.json').read_text('utf-8-sig'))
        assert record['desktop'].startswith('APDC_PerformanceQA_')
        assert Path(record['profile']).resolve()==self.profile.resolve()
        self.u=C.WinDLL('user32',use_last_error=True);self.k=C.WinDLL('kernel32',use_last_error=True)
        u=self.u;k=self.k;u.SetProcessDPIAware()
        k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
        k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)]
        k.CloseHandle.argtypes=[W.HANDLE]
        handle=k.OpenProcess(0x1000,False,record['pid']);assert handle
        buf=C.create_unicode_buffer(32768);length=W.DWORD(len(buf))
        try:
            assert k.QueryFullProcessImageNameW(handle,0,buf,C.byref(length))
            assert Path(buf.value).resolve()==Path(record['path']).resolve()
        finally:k.CloseHandle(handle)
        u.OpenDesktopW.argtypes=[W.LPCWSTR,W.DWORD,W.BOOL,W.DWORD];u.OpenDesktopW.restype=W.HANDLE
        u.SetThreadDesktop.argtypes=[W.HANDLE];u.CloseDesktop.argtypes=[W.HANDLE]
        self.desktop=u.OpenDesktopW(record['desktop'],0,False,0x1ff);assert self.desktop
        assert u.SetThreadDesktop(self.desktop)
        callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        u.EnumDesktopWindows.argtypes=[W.HANDLE,callback,W.LPARAM]
        u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
        u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
        windows=[]
        @callback
        def collect(hwnd,_):
            pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid))
            text=C.create_unicode_buffer(256);u.GetWindowTextW(hwnd,text,len(text))
            if pid.value==record['pid'] and 'Hearts of Iron' in text.value:windows.append(hwnd)
            return True
        u.EnumDesktopWindows(self.desktop,collect,0);assert len(windows)==1,windows
        self.hwnd=windows[0];self.messages=[]
        u.SendMessageTimeoutW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM,W.UINT,W.UINT,C.POINTER(C.c_size_t)]
        u.SendMessageTimeoutW.restype=C.c_ssize_t

    def send(self,message,wparam=0,lparam=0):
        value=C.c_size_t()
        result=self.u.SendMessageTimeoutW(self.hwnd,message,wparam,lparam,0x2,2000,C.byref(value))
        assert result,('window_message_timeout',message,C.get_last_error())
        self.messages.append([message,wparam,lparam])

    def move(self,x,y,held=False):self.send(0x200,int(held),(int(x)&0xffff)|((int(y)&0xffff)<<16))

    def click(self,x,y):
        self.move(x,y);time.sleep(.12)
        self.send(0x201,1,(x&0xffff)|((y&0xffff)<<16));time.sleep(.12)
        self.send(0x202,0,(x&0xffff)|((y&0xffff)<<16));time.sleep(.25)

    def drag(self,x,y,dx,dy):
        self.move(x,y);self.send(0x201,1,(x&0xffff)|((y&0xffff)<<16));time.sleep(.15)
        for step in range(1,9):self.move(x+round(dx*step/8),y+round(dy*step/8),True);time.sleep(.06)
        self.send(0x202,0,((x+dx)&0xffff)|(((y+dy)&0xffff)<<16));time.sleep(.4)

    def close(self):
        self.u.CloseDesktop(self.desktop)
        report={'window_messages':self.messages,'input_desktop_switched':False,'desktop_mouse_or_keyboard_injected':False}
        (self.profile/'private-messages-last.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('action',choices=['click','move','drag']);p.add_argument('coordinates',type=int,nargs='+');a=p.parse_args()
    w=PrivateWindow(a.profile)
    try:getattr(w,a.action)(*a.coordinates)
    finally:w.close()
    print(json.dumps({'status':'messages_delivered','action':a.action,'coordinates':a.coordinates,'input_desktop_switched':False}))
