"""Reimport shipped meshes/animation binaries, inspect full walk cycles and render key poses."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
import numpy as np
def read(rel):return STAGE/rel if (STAGE/rel).exists() else ROOT/rel
def material(definition,mesh,directory):
 folder=Path(directory).name;mat=bpy.data.materials.new(definition.diff[0]);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
 images={}
 for key in ('diff','n','spec'):
  filename=getattr(definition,key)[0];path=read(Path('gfx/models/units')/folder/filename);assert path.exists(),path
  im=bpy.data.images.load(str(path),check_existing=True);im.colorspace_settings.name='sRGB' if key=='diff' else 'Non-Color';node=nodes.new('ShaderNodeTexImage');node.image=im;images[key]=node
 links.new(images['diff'].outputs['Color'],bs.inputs['Base Color'])
 sep=nodes.new('ShaderNodeSeparateColor');links.new(images['spec'].outputs[0],sep.inputs[0]);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(images['spec'].outputs['Alpha'],inv.inputs[1]);links.new(inv.outputs[0],bs.inputs['Roughness'])
 sep=nodes.new('ShaderNodeSeparateColor');links.new(images['n'].outputs[0],sep.inputs[0]);comb=nodes.new('ShaderNodeCombineColor');comb.inputs[2].default_value=1;links.new(sep.outputs['Green'],comb.inputs[0])
 inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(images['n'].outputs['Alpha'],inv.inputs[1]);links.new(inv.outputs[0],comb.inputs[1]);nm=nodes.new('ShaderNodeNormalMap');links.new(comb.outputs[0],nm.inputs['Color']);links.new(nm.outputs[0],bs.inputs['Normal'])
 mesh.materials.append(mat)
io.create_material=material
meshes={};entities={};animations={}
for rel in [p.relative_to(ROOT) for p in (ROOT/'gfx/entities').glob('*.gfx')]+[p.relative_to(STAGE) for p in (STAGE/'gfx/entities').glob('*.gfx')]:
 for root in parse(read(rel).read_text('utf-8-sig')):
  for n in root.children:
   if n.key=='pdxmesh':meshes[n.val('name')]=n
for rel in [p.relative_to(ROOT) for p in (ROOT/'gfx/entities').glob('*.asset')]+[p.relative_to(STAGE) for p in (STAGE/'gfx/entities').glob('*.asset')]:
 for n in parse(read(rel).read_text('utf-8-sig')):
  if n.key=='entity':entities[n.val('name')]=n
for root in (GAME/'gfx/models/units',ROOT/'gfx/models/units',STAGE/'gfx/models/units'):
 for path in root.rglob('animation.asset'):
  for n in parse(path.read_text('utf-8-sig')):
   if n.key=='animation':animations[n.val('name')]=path.parent/n.val('file')
scope=json.loads((WORK/'scope.json').read_text('utf8'));ids=scope['existing_motion_models']+scope['humanoid_vanilla']+scope['seated_upper_vanilla']+scope['new_chibi'];results=[]
expected_ids=set(ids)
if '--only' in sys.argv:
 selected=set(sys.argv[sys.argv.index('--only')+1].split(','));ids=[n for n in ids if n in selected]
 results=[r for r in json.loads((WORK/'roundtrip_validation.partial.json').read_text('utf8')) if r['id'] not in selected]
 for result in results:assert sha(read(meshes[result['id']+'_mesh'].val('file')))==result['mesh_sha256'],'Previously checked mesh changed'
for ident in ids:
 print('VERIFY_BINARY',ident,flush=True);bpy.ops.wm.read_factory_settings(use_empty=True)
 node=meshes[ident+'_mesh'];path=read(node.val('file'));tree=pdx.read_meshfile(str(path))
 for obj in tree.find('object'):
  skel=obj.find('skeleton');bn=[b.tag for b in skel]
  for mesh in obj.findall('mesh'):
   ps=np.array(mesh.get('p')).reshape(-1,3);assert np.isfinite(ps).all();assert len(ps)<65536
   skin=mesh.find('skin');stride=skin.get('bones')[0];ws=np.array(skin.get('w')).reshape(-1,stride);ix=np.array(skin.get('ix')).reshape(-1,stride)
   assert np.max(np.abs(ws.sum(axis=1)-1))<.0001;assert ix[ws>0].min()>=0 and ix[ws>0].max()<len(bn)
 io.import_meshfile(str(path),imp_mesh=True,imp_skel=True,imp_locs=False)
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bodies=[o for o in bpy.data.objects if o.type=='MESH'];rest={b.name:b.head_local.copy() for b in rig.data.bones}
 clips={n.val('id'):animations[n.val('type')] for n in node.children if n.key=='animation'}
 active={n.val('animation') for n in entities[ident+'_entity'].children if n.key=='state'}
 assert active<=clips.keys(),(ident,active-clips.keys());checks=[]
 weapons=[]
 if ident in scope['humanoid_vanilla']+scope['seated_upper_vanilla']:
  before=set(bpy.data.objects);io.import_meshfile(str(path.parent/(ident+'_weapon.mesh')),imp_mesh=True,imp_skel=False,imp_locs=False);gun=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
  for i,n in enumerate(('Right_Hand_node','Left_Hand_node','mid_back_node','Root_node_2')):
   ob=gun if i==0 else gun.copy()
   if i:bpy.context.collection.objects.link(ob)
   weapons.append((ob,n))
 for clip in sorted(active):
  rig.animation_data_clear();clear_pose(rig);io.import_animfile(str(clips[clip]));scene=bpy.context.scene
  assert set(b.tag for b in pdx.read_meshfile(str(clips[clip])).find('info'))<={b.name for b in rig.data.bones}
  frames=list(range(scene.frame_start,scene.frame_end+1)) if clip=='move' else sorted(set([scene.frame_start,(scene.frame_start+scene.frame_end)//2,scene.frame_end]))
  minheight=999;maxspan=0;minbend=999;transforms=[]
  for f in frames:
   scene.frame_set(f);bpy.context.view_layer.update();points=[]
   for ob in bodies:
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());points.extend(ev.matrix_world@Vector(p) for p in ev.bound_box)
   a=np.array([tuple(p) for p in points]);assert np.isfinite(a).all();span=float((a.max(axis=0)-a.min(axis=0)).max());maxspan=max(maxspan,span);minheight=min(minheight,float(a[:,2].min()));assert span<40,(ident,clip,span)
   if clip=='move' and ident not in scope['humanoid_vanilla']+scope['seated_upper_vanilla'] and 'goliath' not in ident and 'helicopter' not in ident:
    for n in rest:
     if not n.endswith('_upper') or n[:-6]+'_foot' not in rest:continue
     lower=n[:-6]+'_lower';foot=n[:-6]+'_foot';h,k,a0=rest[n],rest[lower],rest[foot];axis=(a0-h).normalized();pole=k-h-axis*(k-h).dot(axis);pole=Vector((0,-1,0)) if pole.length<.15 else pole.normalized()
     h,k,a0=[rig.pose.bones[x].matrix.translation for x in (n,lower,foot)];axis=(a0-h).normalized();signed=(k-h-axis*(k-h).dot(axis)).dot(pole);minbend=min(minbend,signed);assert signed>-.0001,(ident,n,f,signed)
   if ident=='APDC_r6_lyuba':
    for n in ('Root','Hip','LeftUpLeg','RightUpLeg','LeftLeg','RightLeg'):
     assert max(abs(rig.pose.bones[n].matrix_basis[i][j]-(1 if i==j else 0)) for i in range(4) for j in range(4))<.002,(ident,clip,n)
   transforms.append(tuple(x for b in rig.pose.bones for row in b.matrix for x in row))
  if clip=='move' and ('helicopter' in ident or 'goliath' in ident):assert minheight>1,(ident,'airborne clearance',minheight)
  checks.append({'clip':clip,'frames_checked':len(frames),'minimum_height':minheight,'max_span':maxspan,'min_knee_plane_projection':minbend if minbend<999 else None})
  if clip in ('move','attack','idle'):
   scene.frame_set(min(scene.frame_end,10 if clip=='move' else 20 if clip=='attack' else 1));bpy.context.view_layer.update()
   for prop,n in weapons:prop.matrix_world=rig.pose.bones[n].matrix;prop.hide_render=max(prop.matrix_world.to_scale())<.001
   render(ident,rig,'binary_'+clip,scene.frame_current)
 results.append({'id':ident,'mesh_sha256':sha(path),'clips':checks});save_json(WORK/'roundtrip_validation.partial.json',results)
assert {r['id'] for r in results}==expected_ids
grounded=json.loads((WORK/'death_ground_validation.json').read_text('utf8')) if (WORK/'death_ground_validation.json').exists() else []
for fix in grounded:
 file=STAGE/'gfx/models/units'/fix['id']/(fix['id']+'_death.anim');assert sha(file)==fix['animation_sha256']
 for result in results:
  if result['id']==fix['id']:
   for check in result['clips']:
    if check['clip']=='death':check.update(minimum_height=fix['minimum_height'],frames_checked=fix['frames_checked'],ground_clearance_rechecked=True)
save_json(WORK/'roundtrip_validation.json',{'status':'PASS','models':results,'actual_binary_meshes_reimported':True,'all_moving_frames_checked':True,'game_runtime_tested':False})
print('ROUNDTRIP_PASS',len(results),flush=True)
