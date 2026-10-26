"""Read-only checks for the Madagascar-only penguin installation."""
from pathlib import Path
import importlib
import json
import math
import re
import struct
import sys
import types
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
MODEL=ROOT/'gfx/models/units/APDC_penguin'
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[sys.argv[1]];sys.modules[pkg.__name__]=pkg
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
config_paths=[ROOT/'gfx/entities/APDC_penguin_infantry.gfx',ROOT/'gfx/entities/zz_APDC_penguin_infantry.asset',MODEL/'animations/animation.asset']
for path in config_paths:
    source=re.sub(r'#[^\n]*','',path.read_text())
    depth=0
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[{}]',source):
        depth+=(token=='{')-(token=='}');assert depth>=0,path
    assert depth==0,path
entity=config_paths[1].read_text()
entities=re.findall(r'\bname\s*=\s*"([^"]+)"',entity)
assert len(entities)==9 and len(set(entities))==9 and all(n.startswith('MAD_infantry') for n in entities)
assert entity.count('scale = 0.77')==3
for parent in re.findall(r'clone\s*=\s*"([^"]+)"',entity):
    assert parent in entities or re.search(r'name\s*=\s*"'+re.escape(parent)+'"',(GAME/'gfx/entities/units_infantry.asset').read_text())
tree=pdx.read_meshfile(str(MODEL/'APDC_penguin.mesh'))
mesh=tree.find('object/APDC_penguinShape/mesh');skeleton=tree.find('object/APDC_penguinShape/skeleton')
original=pdx.read_meshfile(str(GAME/'gfx/models/units/GER_infantry.mesh')).find('object/GER_infantryShape/skeleton')
assert len(skeleton)==33
for a,b in zip(skeleton,original):
    assert (a.tag,a.get('ix'),a.get('pa'))==(b.tag,b.get('ix'),b.get('pa'))
    assert a.get('tx')[:9]==b.get('tx')[:9],a.tag
vertices=len(mesh.get('p'))//3
assert len(mesh.get('tri'))//3==11104 and vertices<65535
assert min(mesh.get('tri'))>=0 and max(mesh.get('tri'))<vertices
for attr,stride in [('p',3),('n',3),('ta',4),('u0',2)]:
    values=mesh.get(attr);assert len(values)==vertices*stride and all(math.isfinite(v) for v in values)
skin=mesh.find('skin');assert skin.get('bones')==[4]
weights=skin.get('w');indices=skin.get('ix');assert len(weights)==len(indices)==vertices*4
for start in range(0,len(weights),4):
    assert abs(sum(weights[start:start+4])-1)<1e-5
    for i in range(start,start+4):
        assert weights[i]>=0
        if weights[i]>0:assert 0<=indices[i]<33
for field in ['diff','n','spec']:
    path=MODEL/mesh.find('material').get(field)[0];raw=path.read_bytes()
    assert raw[:4]==b'DDS ' and raw[84:88]==b'DXT5' and struct.unpack_from('<I',raw,28)[0]==11
    expected=128+sum(max(1,(max(1,1024>>i)+3)//4)**2*16 for i in range(11))
    assert len(raw)==expected
    with Image.open(path) as image:image.load();assert image.size==(1024,1024)
types=set(re.findall(r'type\s*=\s*"([^"]+)"',config_paths[0].read_text()))
registry=dict(re.findall(r'animation\s*=\s*\{\s*name\s*=\s*"([^"]+)"\s*file\s*=\s*"([^"]+)"',config_paths[2].read_text()))
assert types==registry.keys()
for filename in registry.values():
    adapted=pdx.read_meshfile(str(MODEL/'animations'/filename))
    base=pdx.read_meshfile(str(GAME/'gfx/models/units'/filename.removeprefix('APDC_')))
    assert adapted.find('info').attrib==base.find('info').attrib
    for a,b in zip(adapted.find('info'),base.find('info')):
        assert a.tag==b.tag and a.get('sa')==b.get('sa') and a.get('s')==b.get('s')
        assert all(math.isfinite(v) for key in ['t','q','s'] for v in a.get(key))
    assert adapted.find('samples').get('s')==base.find('samples').get('s')
    for attr in ['t','q','s']:
        vals=adapted.find('samples').get(attr,[])
        assert len(vals)==len(base.find('samples').get(attr,[])) and all(math.isfinite(v) for v in vals)
record=json.loads((ROOT/'art_source/penguin_infantry/validation.json').read_text(encoding='utf-8'))
assert record['mesh_and_final_dds_reimported'] and record['animation_bone_compatibility']
assert len(record.get('sampled_animation_checks',[]))==44
assert record['game_runtime_tested'] is False
print(json.dumps({'country':'MAD','entities':len(entities),'triangles':11104,'vertices':vertices,'bones':33,
                  'animation_files':len(registry),'sampled_clips':44,'textures':3,'game_runtime_tested':False}))
