"""Capture settled UI fixture states without changing the input desktop."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROFILE=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_ui_20261107')
OUT=ROOT/'docs/parliament/20261107-ui-corrections/runtime'


def main():
    OUT.mkdir(exist_ok=True);done=set();report=[];deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        game=(PROFILE/'logs/game.log').read_text('utf-8-sig',errors='replace')
        phases=re.findall(r'APDC_UI VISUAL (\w+)',game)
        if phases and phases[-1] not in done:
            phase=phases[-1];done.add(phase);time.sleep(1)
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/cold_war/capture_private.py'),str(PROFILE)],capture_output=True,text=True,encoding='utf-8',timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
            record={'phase':phase,'exit':result.returncode,'metadata':result.stdout.strip(),'error':result.stderr[-600:]}
            if result.returncode==0:(OUT/(phase+'.png')).write_bytes((PROFILE/'private-window.png').read_bytes())
            report.append(record);(OUT/'captures.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(record,ensure_ascii=False),flush=True)
        if 'APDC_UI COMPLETE' in game:
            (OUT/'game.log').write_bytes((PROFILE/'logs/game.log').read_bytes())
            (OUT/'error.log').write_bytes((PROFILE/'logs/error.log').read_bytes())
            (OUT/'system.log').write_bytes((PROFILE/'logs/system.log').read_bytes())
            print('UI fixture complete',flush=True);return
        time.sleep(.3)
    print('UI observation deadline reached',flush=True)


if __name__=='__main__':main()
