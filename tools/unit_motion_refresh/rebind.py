"""Vanilla skeleton binding for tactical doll and seated upper-body-only Lyuba."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
import bmesh,re
UNITS=GAME/'gfx/models/units'
vanilla_tree=pdx.read_meshfile(str(UNITS/'GER_infantry.mesh'))
vanilla_skel=vanilla_tree.find('object/GER_infantryShape/skeleton')
vanilla_asset=(GAME/'gfx/entities/units_infantry.asset').read_text('utf-8-sig')
base=next(n for n in parse(vanilla_asset) if n.val('name')=='infantry_rifle_entity')
vanilla_gfx=(GAME/'gfx/entities/infantry.gfx').read_text('utf-8-sig')
gfxnode=next(n for n in parse(vanilla_gfx)[0].children if n.val('name')=='GER_infantry_rifle_mesh')
animmap={n.val('id'):n.val('type') for n in gfxnode.children if n.key=='animation'}
registry={n.val('name'):UNITS/n.val('file') for n in parse((UNITS/'animation.asset').read_text('utf-8-sig')) if n.key=='animation'}
reports=[];weapon_gfx=[];weapon_assets=[]
def delete_vertices(ob,indices):
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i] for i in indices],context='VERTS');bm.to_mesh(ob.data);bm.free()
def segment(p,a,b,c,d,scale):
 u=b-a;v=d-c;t=(p-a).dot(u)/u.length_squared
 return c+v*t+u.rotation_difference(v)@(p-a-u*t)*scale
for tag in ('tactical_doll','lyuba'):
 ident='APDC_r6_'+tag;entry=sources()[ident];print('REBIND_BEGIN',tag,flush=True)
 bpy.ops.wm.open_mainfile(filepath=entry['blend']);scene=bpy.context.scene;scene.render.fps=30
 old=next(o for o in bpy.data.objects if o.type=='ARMATURE');old.animation_data_clear();old.data.pose_position='REST'
 oldheads={b.name:b.head_local.copy() for b in old.data.bones}
 obs=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==old for m in o.modifiers)]
 oldheight=max(v.co.z for o in obs for v in o.data.vertices);bod=next(o for o in obs if 'gun' in o.vertex_groups)
 gunix=bod.vertex_groups['gun'].index;indices={v.index for v in bod.data.vertices if any(g.group==gunix and g.weight>.9 for g in v.groups)}
 gun=bod.copy();gun.data=bod.data.copy();bpy.context.collection.objects.link(gun);gun.name=ident+'_weapon'
 delete_vertices(gun,[v.index for v in gun.data.vertices if v.index not in indices]);delete_vertices(bod,indices)
 for ob in list(bpy.data.objects):
  if ob not in obs+[gun]:bpy.data.objects.remove(ob,do_unlink=True)
 for ob in obs+[gun]:
  ob.parent=None;ob.matrix_world=Matrix.Identity(4)
  for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 for act in list(bpy.data.actions):bpy.data.actions.remove(act)
 gun.vertex_groups.clear()
 origin=Vector((0,-.62,3.17)) if tag=='tactical_doll' else Vector((-.38,-.66,2.17))
 rotation=64 if tag=='tactical_doll' else 62;fac=.88 if tag=='tactical_doll' else .90
 for v in gun.data.vertices:v.co=Matrix.Rotation(math.radians(rotation),3,'Z')@(v.co-origin)/fac*1.90+Vector((0,-.20,.06))
 io.create_material=lambda *a:None;io.import_meshfile(str(UNITS/'GER_infantry.mesh'),imp_mesh=False,imp_skel=True,imp_locs=False)
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.name=ident+'_GER_rig';rig.data.pose_position='REST'
 heads={b.name:b.head_local.copy() for b in rig.data.bones};limbs={}
 mapping={'root':'Root','hull':'Hip','spine':'back_mid','chest':'back_mid','head':'head','hair':'head','cloak':'back_mid'}
 if tag=='tactical_doll':
  for oldside,newside in [('left','Right'),('right','Left')]:
   for src,dst in [('_upperarm','Arm'),('_forearm','ForeArm'),('_hand','Hand'),('_leg_upper','UpLeg'),('_leg_lower','Leg'),('_leg_foot','Foot')]:mapping[oldside+src]=newside+dst
   for a,b,c,d in [('_upperarm','_forearm','Arm','ForeArm'),('_forearm','_hand','ForeArm','Hand'),('_leg_upper','_leg_lower','UpLeg','Leg'),('_leg_lower','_leg_foot','Leg','Foot')]:limbs[oldside+a]=(oldheads[oldside+a],oldheads[oldside+b],heads[newside+c],heads[newside+d])
 else:
  mapping.update({'hull':'Root','thigh_-1':'Root','shin_-1':'Root','thigh_1':'Root','shin_1':'Root','wheel_-1':'wheel_-1','wheel_1':'wheel_1'})
  static_offset=heads['Hip']-oldheads['spine']*2.3
  select([rig]);bpy.ops.object.mode_set(mode='EDIT')
  for side in (-1,1):
   n='wheel_'+str(side);b=rig.data.edit_bones.new(n);b.head=oldheads[n]*2.3+static_offset;b.tail=b.head+Vector((0,.25,0));b.parent=rig.data.edit_bones['Root']
  bpy.ops.object.mode_set(mode='OBJECT')
  for side,newside in [(-1,'Right'),(1,'Left')]:
   a='arm_'+str(side);b='forearm_'+str(side);mapping[a]=newside+'Arm';mapping[b]=newside+'ForeArm'
   hand=Vector((side*.41,-.70,2.13))
   limbs[a]=(oldheads[a],oldheads[b],heads[newside+'Arm'],heads[newside+'ForeArm'])
   limbs[b]=(oldheads[b],hand,heads[newside+'ForeArm'],heads[newside+'Hand'])
 def transform(p,n):
  if n in limbs:return segment(p,*limbs[n],1.4 if tag=='tactical_doll' else 2.1)
  if tag=='lyuba':
   if n in ('head','hair'):return heads['head']+(p-oldheads['head'])*2.3
   return p*2.3+static_offset
  if n.endswith('_hand'):
   target=mapping[n];side=n.split('_')[0];u=oldheads[n]-oldheads[side+'_forearm'];v=heads[target]-heads[target.replace('Hand','ForeArm')]
   return heads[target]+u.rotation_difference(v)@(p-oldheads[n])*1.4
  if n.endswith('_foot'):
   return segment(p,oldheads[n],oldheads[n]+Vector((0,-.34,-.20)),heads[mapping[n]],heads[mapping[n].replace('Foot','ToeBase')],1.4)
  if n in ('head','hair'):return heads['head']+(p-oldheads['head'])*1.42+Vector((0,0,-.20))
  return Vector((p.x*1.28,p.y*1.4,p.z*1.44+.045))
 for ob in obs:
  names={g.index:g.name for g in ob.vertex_groups};allweights=[]
  for v in ob.data.vertices:
   p=v.co.copy();weights={names[g.group]:g.weight for g in v.groups if g.weight>1e-6};total=sum(weights.values());assert total>0
   v.co=sum((transform(p,n)*w/total for n,w in weights.items()),Vector());nw={}
   for n,w in weights.items():target=mapping[n];nw[target]=nw.get(target,0)+w/total
   if tag=='lyuba':
    for side in (-1,1):
     key='forearm_'+str(side);target=mapping[key]
     if key in weights:
      a,b,_,_=limbs[key];t=max(0,min(1,(p-a).dot(b-a)/(b-a).length_squared));share=max(0,min(1,(t-.75)/.20));amt=nw[target]*share;nw[target]-=amt;nw[target.replace('ForeArm','Hand')]=amt
   allweights.append({n:w for n,w in nw.items() if w>1e-6})
  ob.vertex_groups.clear()
  for b in rig.data.bones:ob.vertex_groups.new(name=b.name)
  for i,weights in enumerate(allweights):
   for n,w in weights.items():ob.vertex_groups[n].add([i],w,'REPLACE')
  ob.parent=rig;ob.modifiers.new('Vanilla_infantry_skin','ARMATURE').object=rig;ob.data.update()
 model=STAGE/'gfx/models/units'/ident;model.mkdir(parents=True,exist_ok=True);select(obs+[rig])
 io.export_meshfile(str(model/(ident+'.mesh')),exp_mesh=True,exp_skel=True,exp_locs=False,exp_selected=True)
 tree=pdx.read_meshfile(str(model/(ident+'.mesh')))
 for obj in tree.find('object'):
  skel=obj.find('skeleton');names={b.get('ix')[0]:b.tag for b in skel};extras=[copy.deepcopy(b) for b in skel if b.tag not in {x.tag for x in vanilla_skel}]
  newskel=[copy.deepcopy(b) for b in vanilla_skel]
  for extra in extras:extra.set('ix',[len(newskel)]);extra.set('pa',[0]);newskel.append(extra)
  ids={b.tag:b.get('ix')[0] for b in newskel}
  for mesh in obj.findall('mesh'):
   skin=mesh.find('skin');skin.set('ix',[ids[names[i]] if i>=0 else i for i in skin.get('ix')])
  skel.clear()
  for b in newskel:skel.append(b)
 for mat in tree.iter('material'):
  for key in ('diff','n','spec'):mat.set(key,[Path(mat.get(key)[0]).with_suffix('.dds').name])
 pdx.write_meshfile(str(model/(ident+'.mesh')),tree)
 select([gun]);io.export_meshfile(str(model/(ident+'_weapon.mesh')),exp_mesh=True,exp_skel=False,exp_locs=False,exp_selected=True)
 wt=pdx.read_meshfile(str(model/(ident+'_weapon.mesh')))
 for mat in wt.iter('material'):
  for key in ('diff','n','spec'):mat.set(key,[Path(mat.get(key)[0]).with_suffix('.dds').name])
 locs=copy.deepcopy(pdx.read_meshfile(str(UNITS/'GER_infantry_weapon_k98_rifle.mesh')).find('locator'))
 for loc in locs:
  pos=[0.0,.364,-2.746] if loc.tag=='muzzle' else [.304,.3963,.161];loc.set('p',pos)
  if loc.get('tx'):tx=list(loc.get('tx'));tx[12:15]=pos;loc.set('tx',tx)
 for oldloc in list(wt.findall('locator')):wt.remove(oldloc)
 wt.append(locs);pdx.write_meshfile(str(model/(ident+'_weapon.mesh')),wt)
 scale=oldheight*(.8 if tag=='tactical_doll' else 1.02)/max(v.co.z for o in obs for v in o.data.vertices)
 weapon_gfx.append(f'pdxmesh = {{ name = "{ident}_weapon_mesh" file = "gfx/models/units/{ident}/{ident}_weapon.mesh" }}')
 wasset=(ROOT/'gfx/entities/APDC_vanilla_infantry.asset').read_text('utf8').replace('APDC_AK12_attachment',ident+'_weapon');weapon_assets.append(wasset)
 entity=vanilla_asset[base.start:base.end].replace('"infantry_rifle_entity"','"'+ident+'_entity"').replace('generic_western_european_rifle_infantry_mesh',ident+'_mesh')
 entity=entity.replace('FRA_infantry_weapon_rifle_right_entity',ident+'_weapon_right_entity').replace('FRA_infantry_weapon_rifle_left_entity',ident+'_weapon_left_entity').replace('FRA_infantry_weapon_rifle_long_idle_entity',ident+'_weapon_right_entity')
 entity=re.sub(r'\bscale\s*=\s*0\.8',f'scale = {scale:.9f}',entity)
 enode=parse(entity)[0];remove=[]
 for n in enode.children:
  if n.key=='state' and n.val('animation')=='long_idle03':remove.append((n.start,n.end,''))
  if n.key=='attach' and n.val('name') not in ('rifle1','rifle2','rifle3','rifle4'):remove.append((n.start,n.end,''))
 entity=patches(entity,remove)
 gfx=vanilla_gfx[gfxnode.start:gfxnode.end].replace('GER_infantry_rifle_mesh',ident+'_mesh').replace('gfx/models/units/GER_infantry.mesh',f'gfx/models/units/{ident}/{ident}.mesh')
 tested=[];rig.data.pose_position='POSE'
 if tag=='lyuba':
  choices={'idle':'idle','idle_look':'long_idle02','idle_shift':'long_idle04','move':'move','attack':'attack','death':'idle'}
  freeze=['Root','Hip']+[n for n in heads if any(x in n for x in ('UpLeg','Leg','Foot','ToeBase'))]
  for clip,sourceclip in choices.items():
   rig.animation_data_clear();clear_pose(rig);io.import_animfile(str(registry[animmap[sourceclip]]));source_action=rig.animation_data.action
   end=scene.frame_end if clip!='death' else 61;sample=[]
   for f in range(1,end+1):
    scene.frame_set(f);sample.append({b.name:b.matrix_basis.copy() for b in rig.pose.bones})
   begin(rig,ident+'_'+clip)
   for f,basis in enumerate(sample,1):
    scene.frame_set(f)
    for b in rig.pose.bones:b.matrix_basis=basis[b.name]
    for n in freeze:rig.pose.bones[n].matrix_basis=Matrix.Identity(4)
    for side in (-1,1):rig.pose.bones['wheel_'+str(side)].rotation_quaternion=Quaternion((1,0,0),(f-1)/30*math.tau*1.1 if clip=='move' else 0)
    if clip=='death':rig.pose.bones['back_mid'].rotation_quaternion=Quaternion((1,0,0),-.48*min(1,(f-1)/35))
    key_all(rig,f)
   export_clip(rig,ident,clip,end);tested.append({'clip':clip,'source':registry[animmap[sourceclip]].name,'frames':end,'root_hip_legs_frozen':True})
  gfx,entity=ensure_asset(ident,list(choices),scale)
  # Vanilla hand nodes still control the four weapon copies in upper-body clips.
  entity=entity[:-2]+''.join(f' attach = {{ name = "rifle{i}" {bn} = "{ident}_weapon_{side}_entity" }}\n' for i,bn,side in [(1,'Right_Hand_node','right'),(2,'Left_Hand_node','left'),(3,'mid_back_node','right'),(4,'Root_node_2','right')])+'}\n'
 else:
  for clip in ('idle','move','attack','support_attack','death','long_idle02','long_idle04','long_idle05'):
   rig.animation_data_clear();clear_pose(rig);io.import_animfile(str(registry[animmap[clip]]));rig.animation_data.action.name=ident+'_'+clip;rig.animation_data.action.use_fake_user=True
   tested.append({'clip':clip,'source':registry[animmap[clip]].name,'frames':scene.frame_end})
 replace_definition('gfx/entities/APDC_r6_models.gfx',ident+'_mesh',gfx)
 replace_definition('gfx/entities/APDC_r6_models.asset',ident+'_entity',entity)
 # Four preview-only props follow the exact game attachment transforms.
 weapons=[]
 for i,n in enumerate(('Right_Hand_node','Left_Hand_node','mid_back_node','Root_node_2')):
  prop=gun if i==0 else gun.copy()
  if i:bpy.context.collection.objects.link(prop)
  weapons.append((prop,n))
 rig.animation_data.action=bpy.data.actions[ident+'_idle'];scene.frame_set(1)
 gun.hide_render=True;save_source(ident,rig,obs)
 for clip,frame in [('idle',1),('move',10),('attack',20)]:
  rig.animation_data.action=bpy.data.actions[ident+'_'+clip];scene.frame_set(frame);bpy.context.view_layer.update()
  for prop,n in weapons:prop.matrix_world=rig.pose.bones[n].matrix;prop.hide_render=max(prop.matrix_world.to_scale())<.001
  render(ident,rig,clip,frame)
 reports.append({'id':ident,'vanilla_bones':33,'extra_wheel_bones':2 if tag=='lyuba' else 0,'scale':scale,'smoking_removed':True,'tests':tested,'lower_body_static':tag=='lyuba'})
 save_json(WORK/'rebind_validation.json',reports)
 print('REBIND_COMPLETE',tag,flush=True)
out=STAGE/'gfx/entities';out.mkdir(exist_ok=True,parents=True)
(out/'APDC_motion_weapons.gfx').write_text('objectTypes = {\n'+'\n'.join(weapon_gfx)+'\n}\n','utf8')
(out/'APDC_motion_weapons.asset').write_text('\n'.join(weapon_assets),'utf8')
