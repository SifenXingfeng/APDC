"""Read-only process memory and phase timing for an isolated, owned QA profile."""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import datetime,json,time,re,sys

class MEMORY(C.Structure):
    _fields_=[('cb',W.DWORD),('PageFaultCount',W.DWORD)]+[(k,C.c_size_t) for k in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]

def run(profile):
    profile=Path(profile);record=profile/'silent-process.json';deadline=time.monotonic()+120
    while True:
        try:
            info=json.loads(record.read_text('utf-8-sig'));break
        except (FileNotFoundError,json.JSONDecodeError):
            if time.monotonic()>deadline:raise RuntimeError('Owned QA did not launch')
            time.sleep(.25)
    kernel=C.WinDLL('kernel32',use_last_error=True);psapi=C.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];kernel.WaitForSingleObject.restype=W.DWORD
    kernel.CloseHandle.argtypes=[W.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes=[W.HANDLE,C.POINTER(MEMORY),W.DWORD];psapi.GetProcessMemoryInfo.restype=W.BOOL
    process=kernel.OpenProcess(0x101000,False,info['pid'])
    if not process:raise OSError(C.get_last_error())
    samples=[];started=datetime.datetime.fromisoformat(info['started']);deadline=time.monotonic()+600
    try:
        while kernel.WaitForSingleObject(process,0)==258 and time.monotonic()<deadline:
            mem=MEMORY();mem.cb=C.sizeof(mem)
            if psapi.GetProcessMemoryInfo(process,C.byref(mem),mem.cb):
                samples.append({'at':datetime.datetime.now().astimezone().isoformat(timespec='milliseconds'),'private_bytes':int(mem.PrivateUsage),'working_set_bytes':int(mem.WorkingSetSize),'peak_working_set_bytes':int(mem.PeakWorkingSetSize),'page_faults':int(mem.PageFaultCount)})
                (profile/'startup-samples.json').write_text(json.dumps(samples,separators=(',',':')),'utf-8')
            time.sleep(2)
    finally:kernel.CloseHandle(process)
    log=(profile/'logs/game.log').read_text('utf-8-sig',errors='replace')
    phases={}
    for name in ['Start RestoreDeviceObjects','End RestoreDeviceObjects','APDC_CW_QA BEGIN','APDC_CW_QA COMPLETE']:
        # Some game lines contain a buffered effect prefix followed by another
        # complete log record. Read the record immediately preceding the marker.
        matches=re.findall(r'\[(\d\d:\d\d:\d\d)\]\[[^\]\n]+\]\[[^\]\n]+\]: '+re.escape(name),log)
        if matches:phases[name]=matches[-1]
    def seconds(a,b):
        return (datetime.datetime.strptime(b,'%H:%M:%S')-datetime.datetime.strptime(a,'%H:%M:%S')).total_seconds()%86400
    report={'profile':str(profile),'pid':info['pid'],'started':info['started'],'phases':phases,'sample_count':len(samples),'peak_private_bytes':max((s['private_bytes'] for s in samples),default=0),'peak_working_set_bytes':max((s['peak_working_set_bytes'] for s in samples),default=0),'final_sample':samples[-1] if samples else None}
    if 'End RestoreDeviceObjects' in phases:
        report['restore_device_seconds']=seconds(phases['Start RestoreDeviceObjects'],phases['End RestoreDeviceObjects'])
        report['launch_to_graphics_ready_seconds']=seconds(started.strftime('%H:%M:%S'),phases['End RestoreDeviceObjects'])
    (profile/'startup-metrics.json').write_text(json.dumps(report,indent=2),'utf-8');print(json.dumps(report))

if __name__=='__main__':run(sys.argv[1])
