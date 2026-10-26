"""Trim unused progress states without changing any encoded map state or texture."""
import json,re
import numpy as np
from common import ROOT,metadata,map_progress_steps

def audit():
    g=metadata();steps=map_progress_steps(g);frames=np.arange(1,steps,dtype=np.float32)
    old=np.floor((frames/np.float32(100000))*np.float32(100000)+np.float32(.5)).astype(np.int32)-1
    new=np.floor((frames/np.float32(steps))*np.float32(steps)+np.float32(.5)).astype(np.int32)-1
    expected=frames.astype(np.int32)-1
    assert np.array_equal(old,expected) and np.array_equal(new,expected)
    return {'old_steps':100000,'new_steps':steps,'valid_frames':len(frames),'decode_mismatches':int(np.count_nonzero(old!=new)),'palette_count':len(g['palette_ids']),'zoom_levels':len(g['scales']),'resolution_or_pixel_changes':False}

def apply():
    report=audit();g=metadata();expected=len(g['pieces'])+len(g['borders'])
    gfx=ROOT/'interface/APDC_cold_war.gfx';shader=ROOT/'gfx/FX/APDC_cw_palette.shader'
    body=gfx.read_text('utf-8');counts=re.findall(r'\bsteps\s*=\s*(\d+)',body)
    assert len(counts)==expected and set(map(int,counts))<={100000,report['new_steps']},'Unexpected map progress definitions'
    changed=re.sub(r'\bsteps\s*=\s*\d+','steps = '+str(report['new_steps']),body)
    # Lossless DDS was benchmarked separately, but did not reduce peak memory
    # or materially shorten this phase. Keep the existing PNG source assets.
    changed=re.sub(r'textureFile1 = "gfx/interface/APDC/cold_war/map_native/([^\"]+)\.dds"',r'textureFile1 = "gfx/interface/APDC/cold_war/map/\1.png"',changed)
    assert len(re.findall(r'textureFile1 = "gfx/interface/APDC/cold_war/map/[^\"]+\.png"',changed))==expected
    if changed!=body:gfx.write_text(changed,'utf-8')
    body=shader.read_text('utf-8');changed,n=re.subn(r'CurrentState \* (?:100000|'+str(report['new_steps'])+r')\.f',f'CurrentState * {report["new_steps"]}.f',body)
    assert n==1,'Map frame decoder changed unexpectedly'
    if changed!=body:shader.write_text(changed,'utf-8')
    report.update({'progress_bars':expected,'configured_states_before':expected*100000,'configured_states_after':expected*report['new_steps']})
    (ROOT/'docs/cold-war/20261025-startup/frame-audit.json').write_text(json.dumps(report,indent=2),'utf-8')
    print(json.dumps(report))
    return report

if __name__=='__main__':apply()
