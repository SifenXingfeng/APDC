"""Resource-only loader fix; assert that tested geometry/skin/rig do not change."""
from pathlib import Path
import sys,types,importlib,json,re,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'art_source/infantry_vanilla_rig';STAGE=WORK/'staging'
MODEL=STAGE/'gfx/models/units/APDC_vanilla_infantry';GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'));from cw import parse,patches
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=['C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh'];sys.modules[pkg.__name__]=pkg
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
def sha(data):return hashlib.sha256(data).hexdigest()
def geometric(node):return (node.tag,node.attrib,[geometric(c) for c in node if c.tag!='material'])
for path in MODEL.glob('*.mesh'):
 tree=pdx.read_meshfile(str(path));before=json.dumps(geometric(tree),sort_keys=True)
 for material in tree.iter('material'):
  for key in ('diff','n','spec'):material.set(key,[material.get(key)[0].replace('APDC_r6_infantry','APDC_vanilla_infantry')])
 pdx.write_meshfile(str(path),tree)
 after=json.dumps(geometric(pdx.read_meshfile(str(path))),sort_keys=True);assert before==after,'Geometry changed during repackage'
manifest=WORK/'backup/manifest.json';records=json.loads(manifest.read_text('utf8'))
base_manifest=ROOT/'art_source/unit_overhaul/backup/manifest.json';base_records=json.loads(base_manifest.read_text('utf8'))
retired=[]
for path in list(MODEL.glob('APDC_r6_infantry*.dds')):
 rel=path.relative_to(STAGE);key=rel.as_posix();newname=path.name.replace('APDC_r6_infantry','APDC_vanilla_infantry')
 assert not (MODEL/newname).exists();path.rename(MODEL/newname)
 for label,root in [('installed',ROOT),('unit_staging',ROOT/'art_source/unit_overhaul/staging')]:
  old=root/rel
  if not old.exists():continue
  assert old.resolve().is_relative_to((root/'gfx/models/units/APDC_vanilla_infantry').resolve())
  assert sha(old.read_bytes())==records[key]['installed_sha256']
  saved=WORK/'backup/retired_duplicate_textures'/label/rel;saved.parent.mkdir(parents=True,exist_ok=True)
  assert not saved.exists();shutil.move(str(old),str(saved))
 records[key]['retired_generated_duplicate']=True;base_records.pop(key,None);retired.append(key)
manifest.write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf8');base_manifest.write_text(json.dumps(base_records,ensure_ascii=False,indent=2),'utf8')
source=(GAME/'gfx/entities/units_infantry.asset').read_text('utf-8-sig')
base=next(n for n in parse(source) if n.val('name')=='infantry_rifle_entity')
entity=source[base.start:base.end].replace('"infantry_rifle_entity"','"APDC_r6_infantry_entity"').replace('generic_western_european_rifle_infantry_mesh','APDC_vanilla_infantry_mesh')
entity=entity.replace('FRA_infantry_weapon_rifle_right_entity','APDC_AK12_attachment_right_entity').replace('FRA_infantry_weapon_rifle_left_entity','APDC_AK12_attachment_left_entity').replace('FRA_infantry_weapon_rifle_long_idle_entity','APDC_AK12_attachment_right_entity')
report=json.loads((WORK/'validation.json').read_text('utf8'));entity=re.sub(r'\bscale\s*=\s*0\.8',f'scale = {report["entity_scale"]:.9f}',entity)
file=STAGE/'gfx/entities/APDC_r6_models.asset';text=file.read_text('utf8');node=next(n for n in parse(text) if n.val('name')=='APDC_r6_infantry_entity')
file.write_text(patches(text,[(node.start,node.end,entity)]),'utf8')
report['mesh_sha256']=sha((MODEL/'APDC_vanilla_infantry.mesh').read_bytes())
report['resource_only_repackage']={'geometry_skin_skeleton_unchanged':True,'retired_duplicate_textures':retired,'state_machine_inlined_from_vanilla':True}
(WORK/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('Repackaged loader references without changing tested vertices, weights, UVs or skeleton.')
