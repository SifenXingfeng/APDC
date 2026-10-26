"""Read-only structural checks of the installed vanilla-rig infantry."""
from pathlib import Path
import importlib,types,sys,json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'art_source/infantry_vanilla_rig'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
MODEL=ROOT/'gfx/models/units/APDC_vanilla_infantry'
ADDON='C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh'
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[ADDON];sys.modules[pkg.__name__]=pkg
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
tree=pdx.read_meshfile(str(MODEL/'APDC_vanilla_infantry.mesh'))
original=pdx.read_meshfile(str(GAME/'gfx/models/units/GER_infantry.mesh')).find('object/GER_infantryShape/skeleton')
vertices=triangles=0
for obj in tree.find('object'):
 skel=obj.find('skeleton');assert [(b.tag,b.attrib) for b in skel]==[(b.tag,b.attrib) for b in original]
 for mesh in obj.findall('mesh'):
  count=len(mesh.get('p'))//3;vertices+=count;triangles+=len(mesh.get('tri'))//3
  assert 0<=min(mesh.get('tri'))<=max(mesh.get('tri'))<count<65536
  skin=mesh.find('skin');stride=skin.get('bones')[0];assert 1<=stride<=4
  for j in range(count):
   weights=skin.get('w')[j*stride:(j+1)*stride];indices=skin.get('ix')[j*stride:(j+1)*stride]
   assert abs(sum(weights)-1)<1e-5 and all(math.isfinite(w) and w>=0 for w in weights)
   assert all(0<=i<33 for i,w in zip(indices,weights) if w>0)
  for v in mesh.get('p'):assert math.isfinite(v)
  for key in ('diff','n','spec'):assert (MODEL/mesh.find('material').get(key)[0]).is_file()
weapon=pdx.read_meshfile(str(MODEL/'APDC_AK12_attachment.mesh'))
muzzle=weapon.find('locator/muzzle').get('p');assert muzzle[2]<-2 and 0<muzzle[1]<1,muzzle
text=(ROOT/'gfx/entities/APDC_r6_models.asset').read_text('utf8')
entity=next(n for n in parse(text) if n.val('name')=='APDC_r6_infantry_entity')
assert entity.val('clone') is None and entity.val('pdxmesh')=='APDC_vanilla_infantry_mesh'
vanilla_text=(GAME/'gfx/entities/units_infantry.asset').read_text('utf-8-sig')
vanilla_entity=next(n for n in parse(vanilla_text) if n.val('name')=='infantry_rifle_entity')
assert [text[n.start:n.end] for n in entity.children if n.key=='state']==[vanilla_text[n.start:n.end] for n in vanilla_entity.children if n.key=='state'],'Full vanilla state machine required'
gfx=parse((ROOT/'gfx/entities/APDC_vanilla_infantry.gfx').read_text('utf8'))[0]
anims=[n.val('type') for m in gfx.children for n in m.children if n.key=='animation']
assert len(anims)==27 and not any('APDC_r6_infantry_' in n for n in anims)
backup=(WORK/'backup/files/gfx/entities/APDC_r6_models.asset').read_text('utf8')
before={n.val('name'):backup[n.start:n.end] for n in parse(backup)}
after={n.val('name'):text[n.start:n.end] for n in parse(text)}
assert before.keys()==after.keys()
assert all(before[n]==after[n] for n in before if n!='APDC_r6_infantry_entity'),'Unrelated R6 model changed'
checks={'status':'PASS','bones':33,'skeleton_and_bind_data_identical_to_vanilla':True,'body_vertices':vertices,'body_triangles':triangles,'original_animation_mappings':27,'other_r6_entities_unchanged':True,'weapon_muzzle':muzzle,'mesh_sha256':hashlib.sha256((MODEL/'APDC_vanilla_infantry.mesh').read_bytes()).hexdigest()}
(WORK/'installed_validation.json').write_text(json.dumps(checks,indent=2),'utf8');print(json.dumps(checks))
