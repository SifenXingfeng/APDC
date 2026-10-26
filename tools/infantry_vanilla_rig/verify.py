"""Reimport the actual exported mesh and exercise original animation files."""
import bpy,sys,types,importlib,logging,json,re,math,argparse,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'art_source/infantry_vanilla_rig'
MODEL=WORK/'staging/gfx/models/units/APDC_vanilla_infantry'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV');UNITS=GAME/'gfx/models/units'
ADDON=Path('C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh')
OUT=WORK/'previews';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'));sys.dont_write_bytecode=True
from cw import parse
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[str(ADDON)];pkg.IO_PDX_LOG=logging.getLogger('pdx');sys.modules[pkg.__name__]=pkg
sub=types.ModuleType('io_pdx_mesh.pdx_blender');sub.__path__=[str(ADDON/'pdx_blender')];sys.modules[sub.__name__]=sub
backend=importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export');pdx=importlib.import_module('io_pdx_mesh.pdx_data')
ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(WORK/'source/APDC_infantry_original_rig.blend'))
materials={}
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image:
   name=Path(node.image.filepath).with_suffix('.dds').name.replace('APDC_r6_infantry','APDC_vanilla_infantry')
   if (MODEL/name).is_file():
    im=bpy.data.images.load(str(MODEL/name),check_existing=True)
    im.colorspace_settings.name='sRGB' if 'diffuse' in name else 'Non-Color';node.image=im
   if 'diffuse' in name:materials[name]=mat
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
def material(definition,mesh,path):mesh.materials.append(materials[definition.diff[0]])
backend.create_material=material
backend.import_meshfile(str(MODEL/'APDC_vanilla_infantry.mesh'),imp_mesh=True,imp_skel=True,imp_locs=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bodies=[o for o in bpy.data.objects if o.type=='MESH']
assert len(rig.data.bones)==33
before=set(bpy.data.objects)
backend.import_meshfile(str(MODEL/'APDC_AK12_attachment.mesh'),imp_mesh=True,imp_skel=False,imp_locs=False)
gun=next(o for o in set(bpy.data.objects)-before if o.type=='MESH');weapons=[]
for i,name in enumerate(('Right_Hand_node','Left_Hand_node','mid_back_node','Root_node_2')):
 ob=gun if i==0 else gun.copy()
 if i:bpy.context.collection.objects.link(ob)
 weapons.append((ob,name))
scene=bpy.context.scene
def attach():
 for ob,b in weapons:
  ob.matrix_world=rig.matrix_world@rig.pose.bones[b].matrix
  ob.hide_render=max(ob.matrix_world.to_scale())<.001

reg={n.val('name'):n.val('file') for n in parse((UNITS/'animation.asset').read_text('utf-8-sig')) if n.key=='animation'}
report=json.loads((WORK/'build_report.json').read_text('utf8'))
files=[]
for key in report['animation_types']:
 f=UNITS/reg[key];assert f.is_file(),f
 info=pdx.read_meshfile(str(f)).find('info')
 assert {n.tag for n in info}<={b.name for b in rig.data.bones},f
 files.append(f)
def clip(path):
 rig.animation_data_clear();rig.data.pose_position='POSE'
 for b in rig.pose.bones:b.matrix_basis.identity()
 backend.import_animfile(str(path));bpy.context.view_layer.update()
def snapshot(frame):
 scene.frame_set(frame);bpy.context.view_layer.update();coords=[]
 for o in bodies:
  ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
  coords.extend(tuple(v.co) for v in me.vertices);ev.to_mesh_clear()
 assert all(math.isfinite(x) for p in coords for x in p)
 spans=[max(p[i] for p in coords)-min(p[i] for p in coords) for i in range(3)]
 assert max(spans)<25,spans
 return {'frame':frame,'span':spans,'center':[(min(p[i] for p in coords)+max(p[i] for p in coords))/2 for i in range(3)]}
tested=[]
if not args.quick:
 for file in files:
  clip(file);frames=sorted(set([scene.frame_start,(scene.frame_start*3+scene.frame_end)//4,(scene.frame_start+scene.frame_end)//2,(scene.frame_start+scene.frame_end*3)//4,scene.frame_end]))
  tested.append({'file':file.name,'samples':[snapshot(f) for f in frames]})
  print('VERIFIED '+file.name,flush=True)
 report['sampled_animation_checks']=tested
else:
 report['sampled_animation_checks']=[]
report['preview_only']=args.quick
report['mesh_sha256']=hashlib.sha256((MODEL/'APDC_vanilla_infantry.mesh').read_bytes()).hexdigest()
report['mesh_reimported']=True;report['game_runtime_tested']=False

world=bpy.data.worlds.new('Studio');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.17,.20,.25,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.6
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.075));floor=bpy.context.object
fm=bpy.data.materials.new('floor');fm.diffuse_color=(.12,.14,.17,1);floor.data.materials.append(fm)
for loc,power,size in [((5,-8,12),1700,7),((-7,-2,8),1400,6),((3,6,10),2000,5)]:
 data=bpy.data.lights.new('Area','AREA');data.energy=power;data.shape='DISK';data.size=size
 ob=bpy.data.objects.new('Area',data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,3.7))-ob.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=9.7
scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=32
scene.render.resolution_x=760;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
previews=[('01_待机','GER_infantry_idle_rifle.anim',1),('02_移动','GER_infantry_moving_rifle.anim',12),('03_站立射击','GER_infantry_attack_stand_rifle.anim',20),('04_蹲姿射击','GER_infantry_attack_crouch_rifle.anim',20),('05_死亡','GER_infantry_death_rifle.anim',-1),('06_训练','GER_infantry_jumping_jacks.anim',15)]
for label,file,frame in previews:
 clip(UNITS/file);scene.frame_set(scene.frame_end if frame<0 else min(frame,scene.frame_end));bpy.context.view_layer.update();attach();snapshot(scene.frame_current)
 target=Vector(snapshot(scene.frame_current)['center'])
 cam.location=target+Vector((10,-18,5.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
 if label in ('01_待机','03_站立射击'):
  cam.location=(12,-3,7);cam.rotation_euler=(Vector((0,0,4.4))-cam.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=7.3
  scene.render.filepath=str(OUT/(label+'_侧面.png'));bpy.ops.render.render(write_still=True);data.ortho_scale=9.7
(WORK/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print('VALIDATION_COMPLETE '+str(len(report.get('sampled_animation_checks',[]))),flush=True)
