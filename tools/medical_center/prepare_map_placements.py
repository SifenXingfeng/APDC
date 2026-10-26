"""Plan (do not write) one land-validated medical-center position per state."""
from pathlib import Path
from collections import defaultdict
from PIL import Image
import hashlib
import json
import math
import re
import sys
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
OUTPUT=Path(sys.argv[1])
building_file=ROOT/'map/buildings.txt'
raw=building_file.read_bytes()
original=raw.decode('utf-8-sig')
assert ';APDC_medical_center;' not in original, 'Positions already exist; do not append duplicates.'
map_image=Image.open(ROOT/'map/provinces.bmp').convert('RGB')
heightmap=Image.open(ROOT/'map/heightmap.bmp').convert('L')
width,height=map_image.size
definitions={}
colour_ids={}
for line in (ROOT/'map/definition.csv').read_text(encoding='utf-8-sig').splitlines():
    fields=line.split(';')
    if len(fields)<8:
        continue
    number=int(fields[0]); rgb=tuple(map(int,fields[1:4]))
    definitions[number]={'colour':rgb,'land':fields[4]=='land'}
    colour_ids[rgb]=number
states={}
for path in (ROOT/'history/states').glob('*.txt'):
    text=re.sub(r'#[^\n]*','',path.read_text(encoding='utf-8-sig'))
    number=int(re.search(r'\bid\s*=\s*(\d+)',text)[1])
    provinces=set(map(int,re.findall(r'\d+',re.search(r'\bprovinces\s*=\s*\{([^}]*)\}',text,re.S)[1])))
    states[number]={p for p in provinces if definitions.get(p,{}).get('land')}
anchors={}; occupied=defaultdict(list)
for line in original.splitlines():
    fields=line.split(';')
    if len(fields)!=7:
        continue
    state=int(fields[0]); x,y,z=map(float,fields[2:5])
    occupied[state].append((x,z))
    if fields[1]=='fuel_silo':
        anchors[state]=(x,z)

def province_at(x,z):
    if not (0<=x<width and 0<=z<height):
        return None
    return colour_ids.get(map_image.getpixel((int(x),height-1-int(z))))
def altitude(x,z):
    return heightmap.getpixel((int(x),height-1-int(z)))*0.1

entries=[]; fallback=[]; tight=[]
pixels=None
for state,land in sorted(states.items()):
    if not land:
        continue
    ax,az=anchors.get(state,(0.0,0.0))
    candidates=[]
    for radius in (0,3,5,7,9,12,16,22):
        for angle in range(0,360,30):
            x=round(ax+radius*math.cos(math.radians(angle)))+0.5
            z=round(az+radius*math.sin(math.radians(angle)))+0.5
            if province_at(x,z) not in land:
                continue
            neighbours=[(x+dx,z+dz) for dx,dz in ((-3,-2),(3,-2),(3,2),(-3,2),(0,0))]
            fit=sum(province_at(u,v) in land for u,v in neighbours)
            valid=[(u,v) for u,v in neighbours if province_at(u,v) in land]
            heights=[altitude(u,v) for u,v in valid]
            relief=max(heights)-min(heights)
            separation=min((math.hypot(x-u,z-v) for u,v in occupied[state]),default=10)
            score=fit*20+min(separation,8)*2-relief*10-radius*0.18
            candidates.append((score,x,z,fit))
    if not candidates:
        fallback.append(state)
        if pixels is None:
            pixels=np.asarray(map_image)
        # Rare fallback for states whose legacy anchors are outside their land.
        coords=[]
        for number in land:
            matches=np.all(pixels==definitions[number]['colour'],axis=2)
            ys,xs=np.nonzero(matches)
            if len(xs):
                pick=len(xs)//2
                coords.append((len(xs),float(xs[pick])+0.5,height-1-float(ys[pick])+0.5))
        assert coords, f'No land pixels for state {state}'
        _,x,z=max(coords)
        candidates=[(0,x,z,1)]
    _,x,z,fit=max(candidates)
    if fit<5:
        tight.append(state)
    assert province_at(x,z) in land
    entries.append(f'{state};APDC_medical_center;{x:.2f};{altitude(x,z):.2f};{z:.2f};0.00;0')

report={'source_sha256':hashlib.sha256(raw).hexdigest(),'source_newline_crlf':b'\r\n' in raw,
        'state_count':len(states),'placement_count':len(entries),'map_size':[width,height],
        'fallback_states':fallback,'tight_footprint_states':tight,
        'end_context':original.splitlines()[-4:],'entries':entries,
        'existing_content_normalized_sha256':hashlib.sha256(original.replace('\r\n','\n').encode()).hexdigest()}
OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('end_context','entries')},ensure_ascii=False))
