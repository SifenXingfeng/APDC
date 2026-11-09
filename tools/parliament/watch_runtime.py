"""Observe QA log milestones and take read-only private-window captures."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PROFILE=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_20261107')
OUT=ROOT/'docs/parliament/20261107-implementation/runtime'


def main(seconds):
    OUT.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+seconds;captured=set();results=[];resized=False
    while time.monotonic()<deadline:
        path=PROFILE/'logs/game.log'
        content=path.read_text('utf-8-sig',errors='replace') if path.exists() else ''
        if 'APDC_PARL_QA START' in content and not resized:
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/parliament/resize_private.py'),str(PROFILE)],capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            resized=result.returncode==0
            print(json.dumps({'resize_exit':result.returncode,'output':result.stdout[-600:],'error':result.stderr[-600:]}),flush=True)
        phases=re.findall(r'APDC_PARL_QA VISUAL (\w+)',content)
        if phases and phases[-1] not in captured:
            phase=phases[-1];captured.add(phase)
            time.sleep(1.2) # Observe the completed 300ms native animation.
            try:
                result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/cold_war/capture_private.py'),str(PROFILE)],capture_output=True,text=True,encoding='utf-8',timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
                meta={'phase':phase,'exit_code':result.returncode,'output':result.stdout[-1200:],'error':result.stderr[-1200:]}
                image=PROFILE/'private-window.png'
                if result.returncode==0 and image.exists():
                    dest=OUT/('visual-'+phase+'.png');dest.write_bytes(image.read_bytes());meta['image']=str(dest)
                results.append(meta)
            except subprocess.TimeoutExpired:results.append({'phase':phase,'error':'Read-only capture timed out'})
            (OUT/'captures.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
        if 'APDC_PARL_QA COMPLETE day35' in content or 'APDC_PARL_QA RELOAD_COMPLETE' in content:
            print('QA reached completion marker',flush=True)
            return
        time.sleep(.5)
    print('Observation timeout',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=int,default=300);main(ap.parse_args().seconds)
