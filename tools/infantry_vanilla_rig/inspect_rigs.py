import bpy,sys,json,types,importlib,logging
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'art_source/infantry_vanilla_rig';OUT.mkdir(parents=True,exist_ok=True)
ADDON=Path('C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh')
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[str(ADDON)];pkg.IO_PDX_LOG=logging.getLogger('pdx');sys.modules[pkg.__name__]=pkg
sub=types.ModuleType('io_pdx_mesh.pdx_blender');sub.__path__=[str(ADDON/'pdx_blender')];sys.modules[sub.__name__]=sub
backend=importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
def riginfo(rig):
 return [{'name':b.name,'parent':b.parent.name if b.parent else None,'head':list(b.head_local),'tail':list(b.tail_local),'matrix':[list(r) for r in b.matrix_local]} for b in rig.data.bones]
bpy.ops.wm.open_mainfile(filepath='D:/Desktop/剩余六套单位与步枪_待接入/可编辑源文件/通用步兵人物/APDC_r6_infantry.blend')
old=next(o for o in bpy.data.objects if o.type=='ARMATURE');record={'custom':riginfo(old),'meshes':[]}
for o in bpy.data.objects:
 if o.type!='MESH':continue
 groups={g.index:g.name for g in o.vertex_groups}
 counts={}
 for v in o.data.vertices:
  if v.groups:
   g=groups[max(v.groups,key=lambda g:g.weight).group];counts[g]=counts.get(g,0)+1
 record['meshes'].append({'name':o.name,'bbox':[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)],'group_counts':counts})
bpy.ops.wm.read_factory_settings(use_empty=True)
backend.create_material=lambda *a:None
backend.import_meshfile(str(GAME/'gfx/models/units/GER_infantry.mesh'),imp_mesh=True,imp_skel=True,imp_locs=True)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');record['vanilla']=riginfo(rig)
record['vanilla_meshes']=[{'name':o.name,'bbox':[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)]} for o in bpy.data.objects if o.type=='MESH']
(OUT/'rig_inspection.json').write_text(json.dumps(record,indent=2),'utf8')
for key in ('custom','vanilla'):
 print(key,[(b['name'],[round(x,3) for x in b['head']]) for b in record[key]])
print(record['meshes']);print(record['vanilla_meshes'])
bpy.ops.wm.read_factory_settings(use_empty=True)
backend.import_meshfile(str(GAME/'gfx/models/units/GER_infantry_weapon_k98_rifle.mesh'),imp_mesh=True,imp_skel=True,imp_locs=True)
print('WEAPON',[(o.name,o.type,list(o.location),[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)] if o.type=='MESH' else None) for o in bpy.data.objects])
