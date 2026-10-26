"""Read-only capture after each visibility stage has rendered; no UI input."""
import sys,time,json,re,subprocess,shutil
from pathlib import Path

def run(profile):
    profile=Path(profile);deadline=time.monotonic()+330;done={};script=Path(__file__).with_name('capture_private.py')
    while time.monotonic()<deadline:
        log=profile/'logs/game.log'
        text=log.read_text('utf-8-sig',errors='replace') if log.exists() else ''
        for stage,day in re.findall(r'APDC_CW_VISIBILITY STAGE (\w+) day=(\d+)',text):
            if stage in done:continue
            # Two subsequent daily ticks prove native rendering resumed after
            # the state change, avoiding a capture of a previous frame.
            days=[int(d) for d in re.findall(r'APDC_CW_VISIBILITY DAY (\d+)',text)]
            if not days or max(days)<int(day)+2:continue
            subprocess.run([sys.executable,str(script),str(profile)],check=True,capture_output=True)
            target=profile/('visibility-'+stage.lower()+'.png');shutil.copy2(profile/'private-window.png',target);done[stage]=str(target)
            print(json.dumps({'captured':stage,'image':str(target)}),flush=True)
        (profile/'visibility-captures.json').write_text(json.dumps(done,indent=2),'utf-8')
        if len(done)==5 and 'APDC_CW_QA PASS global_daily_batch_runs_once' in text:
            print(json.dumps({'complete':True,'stages':list(done)}),flush=True);return
        time.sleep(.5)
    raise RuntimeError('Visibility capture sequence did not finish')

if __name__=='__main__':run(sys.argv[1])
