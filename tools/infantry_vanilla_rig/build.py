"""Rebind the approved infantry art to the unmodified German infantry skeleton."""
import bpy,bmesh,sys,types,importlib,logging,json,copy,math,shutil,re,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'art_source/infantry_vanilla_rig';STAGE=WORK/'staging'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV');UNITS=GAME/'gfx/models/units'
ADDON=Path('C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh')
MODEL=STAGE/'gfx/models/units/APDC_vanilla_infantry';MODEL.mkdir(parents=True,exist_ok=True)
SOURCE=WORK/'source';SOURCE.mkdir(parents=True,exist_ok=True)
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,patches
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[str(ADDON)];pkg.IO_PDX_LOG=logging.getLogger('pdx');sys.modules[pkg.__name__]=pkg
sub=types.ModuleType('io_pdx_mesh.pdx_blender');sub.__path__=[str(ADDON/'pdx_blender')];sys.modules[sub.__name__]=sub
backend=importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
pdx=importlib.import_module('io_pdx_mesh.pdx_data')

bpy.ops.wm.open_mainfile(filepath='D:/Desktop/剩余六套单位与步枪_待接入/可编辑源文件/通用步兵人物/APDC_r6_infantry.blend')
bpy.context.preferences.filepaths.save_version=0
old=next(o for o in bpy.data.objects if o.type=='ARMATURE')
old.animation_data_clear();old.data.pose_position='REST'
old_heads={b.name:b.head_local.copy() for b in old.data.bones}
body=bpy.data.objects['APDC_r6_infantry'];head=bpy.data.objects['APDC_r6_infantry_vanilla_head']
for o in list(bpy.data.objects):
 if o not in (old,body,head):bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
for ob in (body,head):
 ob.parent=None
 for m in list(ob.modifiers):ob.modifiers.remove(m)
bpy.data.objects.remove(old,do_unlink=True)
backend.create_material=lambda *a:None
backend.import_meshfile(str(UNITS/'GER_infantry.mesh'),imp_mesh=False,imp_skel=True,imp_locs=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
rig.name='APDC_UNMODIFIED_GER_INFANTRY_33_BONES';rig.data.pose_position='REST'
heads={b.name:b.head_local.copy() for b in rig.data.bones}
donor=pdx.read_meshfile(str(UNITS/'GER_infantry.mesh')).find('object/GER_infantryShape')
donor_mesh=donor.find('mesh');donor_skin=donor_mesh.find('skin');donor_positions=donor_mesh.get('p')
donor_bones={b.get('ix')[0]:b.tag for b in donor.find('skeleton')}
donor_stride=donor_skin.get('bones')[0];donor_weights=donor_skin.get('w');donor_indices=donor_skin.get('ix')
face_lookup=KDTree(len(donor_positions)//3)
for i in range(len(donor_positions)//3):
 x,z,ny=donor_positions[i*3:i*3+3]
 face_lookup.insert((x*.62,ny*.62+.015,(z-6.36)*.62+4.352),i)
face_lookup.balance()

def remove_vertices(ob,indices):
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
 bmesh.ops.delete(bm,geom=[bm.verts[i] for i in indices],context='VERTS')
 bm.to_mesh(ob.data);bm.free();ob.data.update()

gun_group=body.vertex_groups['gun'].index
gun_indices={v.index for v in body.data.vertices if any(g.group==gun_group and g.weight>.9 for g in v.groups)}
weapon=body.copy();weapon.data=body.data.copy();bpy.context.collection.objects.link(weapon)
weapon.name='APDC_AK12_vanilla_attachment';weapon.data.name=weapon.name+'Shape'
remove_vertices(weapon,[v.index for v in weapon.data.vertices if v.index not in gun_indices])
remove_vertices(body,gun_indices)
# The extracted vanilla head already contains its own skinned neck transition.
# Remove the additional procedural flesh cylinder; stacking both produced a
# second, stretched strip on the back of the neck in the original aiming pose.
head_group=body.vertex_groups['head'].index
neck_indices={v.index for v in body.data.vertices if 4.229<=v.co.z<=4.441 and abs(v.co.x)<.14 and -.11<v.co.y<.20 and any(g.group==head_group and g.weight>.99 for g in v.groups)}
remove_vertices(body,neck_indices)
weapon.parent=None;weapon.matrix_world=Matrix.Identity(4)
for m in list(weapon.modifiers):weapon.modifiers.remove(m)
weapon.vertex_groups.clear()
# Restore authored weapon-local geometry, then fit to the vanilla K98 attachment
# coordinate convention. Only the visible prop's exterior is transformed.
undo=Matrix.Rotation(math.radians(64),3,'Z')
for v in weapon.data.vertices:
 p=undo@(v.co-Vector((0,-.56,3.18)))/.85
 v.co=p*1.90+Vector((0,-.20,.06))

def segment(p,a,b,c,d,radius_scale=1.4):
 a,b,c,d=map(Vector,(a,b,c,d));u=b-a;v=d-c
 t=(p-a).dot(u)/u.length_squared;rad=p-a-u*t
 return c+v*t+u.rotation_difference(v)@rad*radius_scale

mapping={'root':'Root','hull':'Hip','spine':'back_mid','chest':'back_mid','head':'head','hair':'head','cloak':'back_mid'}
limbs={}
# The old generator called negative-X limbs 'left'; the vanilla rig names them Right.
for old_side,new_side in [('left','Right'),('right','Left')]:
 for src,dst in [('_upperarm','Arm'),('_forearm','ForeArm'),('_hand','Hand'),('_leg_upper','UpLeg'),('_leg_lower','Leg'),('_leg_foot','Foot')]:
  mapping[old_side+src]=new_side+dst
 for a,b,c,d in [('_upperarm','_forearm','Arm','ForeArm'),('_forearm','_hand','ForeArm','Hand'),('_leg_upper','_leg_lower','UpLeg','Leg'),('_leg_lower','_leg_foot','Leg','Foot')]:
  limbs[old_side+a]=(old_heads[old_side+a],old_heads[old_side+b],heads[new_side+c],heads[new_side+d])

def transform(p,bone):
 if bone in limbs:return segment(p,*limbs[bone])
 if bone.endswith('_hand'):
  side=bone.split('_')[0];new=mapping[bone]
  u=old_heads[bone]-old_heads[side+'_forearm'];v=heads[new]-heads[new.replace('Hand','ForeArm')]
  return heads[new]+u.rotation_difference(v)@(p-old_heads[bone])*1.4
 if bone.endswith('_foot'):
  side=bone.split('_')[0];a=old_heads[bone];target=heads[mapping[bone]]
  toe=heads[mapping[bone].replace('Foot','ToeBase')]
  return segment(p,a,a+Vector((0,-.34,-.20)),target,toe,1.4)
 if bone in ('head','hair'):
  return heads['head']+(p-old_heads['head'])*1.42+Vector((0,0,-.20))
 if bone=='hull':
  extension=.24*max(0,min(1,(2.8-p.z)/.37))
  return Vector((p.x*1.28,p.y*1.4,p.z*1.44+.045-extension))
 return Vector((p.x*1.28,p.y*1.4,p.z*1.44+.045))

stats=[]
for ob in (body,head):
 names={g.index:g.name for g in ob.vertex_groups};weights=[]
 for v in ob.data.vertices:
  original_co=v.co.copy()
  old_w={names[g.group]:g.weight for g in v.groups if g.weight>1e-7}
  total=sum(old_w.values());assert total>0
  v.co=sum((transform(v.co,n)*(w/total) for n,w in old_w.items()),Vector())
  nw={}
  for n,w in old_w.items():
   target=mapping[n];nw[target]=nw.get(target,0)+w/total
  if ob==head:
   # The borrowed face keeps its donor's real head/neck skin weights. Do not
   # flatten the jaw by applying a height-only neck blend to facial vertices.
   _,source_i,distance=face_lookup.find(original_co);assert distance<.001,distance
   nw={}
   for j in range(donor_stride):
    pos=source_i*donor_stride+j;w=donor_weights[pos]
    if w>1e-7:
     n=donor_bones[donor_indices[pos]];nw[n]=nw.get(n,0)+w
  elif 'head' in nw and original_co.z<4.40:
   # The neck base stays inside the collar when the head looks up or sideways.
   follow=max(0,min(1,(original_co.z-4.24)/.16))
   amount=nw['head']*(1-follow);nw['head']-=amount;nw['back_mid']=nw.get('back_mid',0)+amount
  if 'Hip' in nw and original_co.z<2.82:
   side='Left' if original_co.x>0 else 'Right'
   share=.75*max(0,min(1,(2.82-original_co.z)/.35))*min(1,abs(original_co.x)/.18)
   amount=nw['Hip']*share;nw['Hip']-=amount;nw[side+'UpLeg']=nw.get(side+'UpLeg',0)+amount
  # Let the wrist twist be shared with the original roll joint, not a hard seam.
  for side in ('Left','Right'):
   key=side+'ForeArm'
   if key in nw:
    a=heads[key];b=heads[side+'Hand'];t=max(0,min(1,(v.co-a).dot(b-a)/(b-a).length_squared))
    share=max(0,min(.85,(t-.35)/.65))
    if share>0:nw[side+'ForeArmRoll']=nw[key]*share;nw[key]*=1-share
  nw=dict(sorted(nw.items(),key=lambda x:-x[1])[:4]);s=sum(nw.values());weights.append({k:w/s for k,w in nw.items()})
 ob.vertex_groups.clear()
 for b in rig.data.bones:ob.vertex_groups.new(name=b.name)
 for i,ws in enumerate(weights):
  for n,w in ws.items():ob.vertex_groups[n].add([i],w,'REPLACE')
 for m in list(ob.modifiers):ob.modifiers.remove(m)
 ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 ob.modifiers.new('Original_GER_skin','ARMATURE').object=rig
 ob.data.update()
 stats.append({'object':ob.name,'vertices':len(ob.data.vertices),'max_influences':max(map(len,weights))})
body.name='APDC_vanilla_infantry';body.data.name='APDC_vanilla_infantryShape'
head.name='APDC_vanilla_infantry_face';head.data.name='APDC_vanilla_infantryFaceShape'

def select(objects):
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0]

select([body,head,rig])
body_path=MODEL/'APDC_vanilla_infantry.mesh'
backend.export_meshfile(str(body_path),exp_mesh=True,exp_skel=True,exp_locs=False,exp_selected=True)
tree=pdx.read_meshfile(str(body_path));original=pdx.read_meshfile(str(UNITS/'GER_infantry.mesh')).find('object/GER_infantryShape/skeleton')
max_bind_error=0
for obj in tree.find('object'):
 skel=obj.find('skeleton');assert skel is not None and len(skel)==33
 exported_names={b.get('ix')[0]:b.tag for b in skel};vanilla_ids={b.tag:b.get('ix')[0] for b in original}
 for mesh in obj.findall('mesh'):
  skin=mesh.find('skin');skin.set('ix',[vanilla_ids[exported_names[i]] if i>=0 else i for i in skin.get('ix')])
 for b in skel:
  if b.tag in {mapping[k] for k in mapping if k!='root'}:
   ref=next(x for x in original if x.tag==b.tag)
   max_bind_error=max(max_bind_error,max(abs(x-y) for x,y in zip(b.get('tx'),ref.get('tx'))))
 # Preserve byte-equivalent original inverse bind data, including tiny-scale nodes.
 skel.clear()
 for b in original:skel.append(copy.deepcopy(b))
assert max_bind_error<.002,max_bind_error
for material in tree.iter('material'):
 for key in ('diff','n','spec'):
  material.set(key,[Path(material.get(key)[0]).with_suffix('.dds').name.replace('APDC_r6_infantry','APDC_vanilla_infantry')])
pdx.write_meshfile(str(body_path),tree)

select([weapon]);weapon_path=MODEL/'APDC_AK12_attachment.mesh'
backend.export_meshfile(str(weapon_path),exp_mesh=True,exp_skel=False,exp_locs=False,exp_selected=True)
wt=pdx.read_meshfile(str(weapon_path))
for material in wt.iter('material'):
 for key in ('diff','n','spec'):material.set(key,[Path(material.get(key)[0]).with_suffix('.dds').name.replace('APDC_r6_infantry','APDC_vanilla_infantry')])
# Copy vanilla locator conventions, then place muzzle/cartridge on the new prop.
ref=pdx.read_meshfile(str(UNITS/'GER_infantry_weapon_k98_rifle.mesh'))
locs=copy.deepcopy(ref.find('locator'))
if locs is not None:
 for loc in locs:
  # io_pdx_mesh swaps Y/Z without sign reversal (a handedness change).
  co=Vector((0,-1.34,.16))*1.9+Vector((0,-.20,.06)) if loc.tag=='muzzle' else Vector((.16,.19,.177))*1.9+Vector((0,-.20,.06))
  loc.set('p',[co.x,co.z,co.y])
  if loc.get('tx'):
   tx=list(loc.get('tx'));tx[12:15]=loc.get('p');loc.set('tx',tx)
 for empty in list(wt.findall('locator')):wt.remove(empty)
 wt.append(locs)
pdx.write_meshfile(str(weapon_path),wt)
for p in (ROOT/'gfx/models/units/APDC_r6_infantry').glob('*.dds'):shutil.copy2(p,MODEL/p.name.replace('APDC_r6_infantry','APDC_vanilla_infantry'))

max_z=max(v.co.z for o in (body,head) for v in o.data.vertices)
entity_scale=5.240162372589111*.8/max_z
gfx=(GAME/'gfx/entities/infantry.gfx').read_text('utf-8-sig')
wrapper=parse(gfx)[0]
mesh=next(n for n in wrapper.children if n.key=='pdxmesh' and n.val('name')=='GER_infantry_rifle_mesh')
mesh_text=gfx[mesh.start:mesh.end].replace('GER_infantry_rifle_mesh','APDC_vanilla_infantry_mesh').replace('gfx/models/units/GER_infantry.mesh','gfx/models/units/APDC_vanilla_infantry/APDC_vanilla_infantry.mesh')
rel=Path('gfx/entities/APDC_vanilla_infantry.gfx');(STAGE/rel).parent.mkdir(parents=True,exist_ok=True)
(STAGE/rel).write_text('objectTypes = {\n'+mesh_text+'\n pdxmesh = { name = "APDC_AK12_attachment_mesh" file = "gfx/models/units/APDC_vanilla_infantry/APDC_AK12_attachment.mesh" }\n}\n','utf8')
asset=(GAME/'gfx/entities/units_infantry.asset').read_text('utf-8-sig')
entities=parse(asset)
left=next(n for n in entities if n.key=='entity' and n.val('name')=='GER_infantry_weapon_rifle_left_entity')
left_text=asset[left.start:left.end].replace('GER_infantry_weapon_rifle_left_entity','APDC_AK12_attachment_left_entity').replace('GER_infantry_weapon_rifle_mesh','APDC_AK12_attachment_mesh')
left_text=re.sub(r'\banimation\s*=\s*"[^"]+"','',left_text)
weapons=left_text+'\nentity = { name = "APDC_AK12_attachment_right_entity" pdxmesh = "APDC_AK12_attachment_mesh" scale = 1 }\n'
(STAGE/'gfx/entities/APDC_vanilla_infantry.asset').write_text(weapons,'utf8')
base=next(n for n in entities if n.val('name')=='infantry_rifle_entity')
new_entity=asset[base.start:base.end].replace('"infantry_rifle_entity"','"APDC_r6_infantry_entity"').replace('generic_western_european_rifle_infantry_mesh','APDC_vanilla_infantry_mesh')
new_entity=new_entity.replace('FRA_infantry_weapon_rifle_right_entity','APDC_AK12_attachment_right_entity').replace('FRA_infantry_weapon_rifle_left_entity','APDC_AK12_attachment_left_entity').replace('FRA_infantry_weapon_rifle_long_idle_entity','APDC_AK12_attachment_right_entity')
new_entity=re.sub(r'\bscale\s*=\s*0\.8',f'scale = {entity_scale:.9f}',new_entity)
old_asset=(ROOT/'gfx/entities/APDC_r6_models.asset').read_text('utf-8-sig')
node=next(n for n in parse(old_asset) if n.val('name')=='APDC_r6_infantry_entity')
(STAGE/'gfx/entities/APDC_r6_models.asset').write_text(patches(old_asset,[(node.start,node.end,new_entity)]),'utf8')

# Keep a clean source with original rest rig; preview/export only copies.
rig.data.pose_position='REST';weapon.hide_render=True;weapon.hide_set(True)
select([body,head,rig]);bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'APDC_infantry_original_rig.blend'))
bpy.ops.export_scene.fbx(filepath=str(SOURCE/'APDC_infantry_original_rig.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True,axis_forward='-Z',axis_up='Y')
record={'skeleton':'GER_infantry.mesh','bones':33,'vanilla_bind_data_exact':True,'max_export_bind_error':max_bind_error,'entity_scale':entity_scale,'mesh_objects':stats,'weapon_split':True,'animation_types':[n.val('type') for n in mesh.children if n.key=='animation'],'scope':'generic infantry only; tactical dolls, UMP and penguin unchanged','input_r6_asset_sha256':hashlib.sha256((ROOT/'gfx/entities/APDC_r6_models.asset').read_bytes()).hexdigest()}
(WORK/'build_report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf8')
print('BUILD_COMPLETE '+json.dumps(record,ensure_ascii=False),flush=True)
