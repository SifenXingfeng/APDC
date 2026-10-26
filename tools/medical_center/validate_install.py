"""Read-only installation checks. This does not replace an in-game load test."""
from pathlib import Path
from PIL import Image
from collections import Counter
import hashlib
import importlib
import json
import math
import re
import struct
import sys
import types

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
package=types.ModuleType('io_pdx_mesh'); package.__path__=[sys.argv[1]]
sys.modules[package.__name__]=package
data=importlib.import_module('io_pdx_mesh.pdx_data')
paths=['common/buildings/APDC_medical_center.txt','common/technologies/APDC_medical_center.txt',
       'common/on_actions/APDC_medical_center.txt','gfx/entities/APDC_medical_center.gfx',
       'gfx/entities/APDC_medical_center.asset','interface/zz_APDC_medical_center.gfx']
for rel in paths:
    text=(ROOT/rel).read_text(encoding='utf-8-sig')
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|#[^\n]*|[{}]|[^\s{}]+',text)
    level=0
    for token in tokens:
        if token.startswith('#'):
            continue
        level+=(token=='{')-(token=='}')
        assert level>=0,rel
    assert level==0,rel
definition=(ROOT/paths[0]).read_text()
assert 'state_max = 1' in definition and 'icon_frame = 32' in definition
assert 'state_modifiers' not in definition and 'country_modifiers' not in definition
assert 'popup = no' in (ROOT/paths[2]).read_text()
for lang in ('english','simp_chinese'):
    path=ROOT/f'localisation/{lang}/APDC_medical_center_l_{lang}.yml'
    raw=path.read_bytes()
    assert raw.startswith(b'\xef\xbb\xbf'),path
    assert raw.decode('utf-8-sig').startswith('l_'+lang+':')

model=ROOT/'gfx/models/buildings/APDC_medical_center'
tree=data.read_meshfile(str(model/'APDC_medical_center.mesh'))
mesh=tree.find('object').find('APDC_medical_centerShape').find('mesh')
vertex_count=len(mesh.get('p'))//3
assert len(mesh.get('n'))==vertex_count*3
assert len(mesh.get('ta'))==vertex_count*4
assert len(mesh.get('u0'))==vertex_count*2
assert len(mesh.get('tri'))%3==0 and max(mesh.get('tri'))<vertex_count
assert min(mesh.get('tri'))>=0
for attr in ('p','n','ta','u0'):
    assert all(math.isfinite(v) for v in mesh.get(attr)),attr
assert vertex_count<65535
assert len(mesh.get('tri'))//3==9814
for channel in ('diff','n','spec'):
    path=model/mesh.find('material').get(channel)[0]
    raw=path.read_bytes()
    assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5'
    assert struct.unpack_from('<I',raw,28)[0]==11
    expected=128+sum(max(1,(max(1,1024>>i)+3)//4)**2*16 for i in range(11))
    assert len(raw)==expected,(path,len(raw),expected)
    with Image.open(path) as image:
        assert image.size==(1024,1024)
        image.load()
with Image.open(GAME/'gfx/interface/buildings/building_icon_strip.dds') as image:
    original=image.convert('RGBA')
with Image.open(ROOT/'gfx/interface/buildings/APDC_building_icon_strip.dds') as image:
    strip=image.convert('RGBA')
assert strip.size==(1472,46)
assert strip.crop((0,0,1426,46)).tobytes()==original.tobytes()
placements=[line for line in (ROOT/'map/buildings.txt').read_text().splitlines() if ';APDC_medical_center;' in line]
counts=Counter(int(line.split(';')[0]) for line in placements)
assert len(counts)==2525 and set(counts.values())=={1}
assert (ROOT/'art_source/medical_center/model_validation.json').is_file()
record=json.loads((ROOT/'art_source/medical_center/model_validation.json').read_text(encoding='utf-8'))
assert record['mesh_binary_roundtrip'] and record['final_dds_and_mesh_rendered']
assert record['game_runtime_tested'] is False
print(json.dumps({'config_files_checked':len(paths),'localisation_bom_valid':True,
                  'triangles':len(mesh.get('tri'))//3,'vertices':vertex_count,'dds_mipmap_levels':11,
                  'preserved_icon_frames':31,'map_placements':len(counts),'game_runtime_tested':False},ensure_ascii=False))
