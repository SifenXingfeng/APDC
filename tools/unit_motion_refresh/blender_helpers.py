from common import *
import bpy,math,copy
from mathutils import Vector,Matrix,Quaternion,Euler
io=backend()
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
def clear_pose(rig):
 for b in rig.pose.bones:
  b.rotation_mode='QUATERNION';b.matrix_basis=Matrix.Identity(4)
def key_all(rig,frame):
 for b in rig.pose.bones:
  for key in ('location','rotation_quaternion','scale'):b.keyframe_insert(key,frame=frame,group=b.name)
def begin(rig,clip):
 rig.animation_data_clear();rig.animation_data_create();action=bpy.data.actions.new(clip);action.use_fake_user=True;rig.animation_data.action=action
 clear_pose(rig);return action
def export_clip(rig,ident,clip,frames):
 bpy.context.view_layer.objects.active=rig
 for fc in rig.animation_data.action.fcurves:
  for key in fc.keyframe_points:key.interpolation='LINEAR'
 out=STAGE/'gfx/models/units'/ident;out.mkdir(parents=True,exist_ok=True)
 io.export_animfile(str(out/(ident+'_'+clip+'.anim')),frame_start=1,frame_end=frames)
def stable_ik(hip,knee,foot,target,pole):
 h,k,a,t=map(Vector,(hip,knee,foot,target));l1=(k-h).length;l2=(a-k).length
 direction=t-h;dist=max(abs(l1-l2)+.001,min(direction.length,l1+l2-.02));v=direction.normalized();t=h+v*dist
 projected=Vector(pole)-v*Vector(pole).dot(v)
 assert projected.length>.05,'Pole singularity'
 bend=projected.normalized();along=(l1*l1+dist*dist-l2*l2)/(2*dist)
 middle=h+v*along+bend*math.sqrt(max(0,l1*l1-along*along))
 assert (middle-h-v*(middle-h).dot(v)).dot(bend)>0
 return middle,t
def set_chain(rig,leg,target,bob=0):
 h,k,a=[Vector(leg[x]) for x in ('hip','knee','ankle')];delta=Vector((0,0,bob));pole=Vector(leg['pole'])
 mid,end=stable_ik(h+delta,k+delta,a+delta,target,pole)
 for bn,p0,p1,n0,n1 in ((leg['bones'][0],h,k,h+delta,mid),(leg['bones'][1],k,a,mid,end)):
  q=(p1-p0).rotation_difference(n1-n0);rig.pose.bones[bn].matrix=Matrix.Translation(n0)@q.to_matrix().to_4x4()@rig.data.bones[bn].matrix_local.to_3x3().to_4x4();bpy.context.view_layer.update()
 rig.pose.bones[leg['bones'][2]].matrix=Matrix.Translation(end)@rig.data.bones[leg['bones'][2]].matrix_local.to_3x3().to_4x4();bpy.context.view_layer.update()
 return (mid-(h+delta)).dot(pole)

def reachable_body_offset(legs,cfg,bob_function):
 # Long, nearly straight original struts need a small crouch, otherwise IK
 # clamps a planted foot above the floor near the ends of the stride.
 from gaits import foot_path
 offset=0.
 for i in range(201):
  t=i/200;bob=bob_function(t)
  for leg in legs:
   h,k,a=[Vector(leg[x]) for x in ('hip','knee','ankle')]
   dy,dz,_=foot_path(t,leg['phase'],cfg['stride'],cfg['lift'],cfg['duty'])
   target=a+Vector((0,dy,dz));reach=(k-h).length+(a-k).length-.025
   horizontal=(target.x-h.x)**2+(target.y-h.y)**2
   assert horizontal<reach**2,('Stride wider than limb reach',leg['bones'])
   ceiling=target.z+math.sqrt(reach**2-horizontal)-h.z
   offset=min(offset,ceiling-bob-.006)
 return offset
def ensure_asset(ident,clips,scale,particle=None,locator='barrel',weapon=False):
 folder=STAGE/'gfx/models/units'/ident;folder.mkdir(parents=True,exist_ok=True)
 (folder/'animation.asset').write_text('\n'.join(f'animation = {{ name = "{ident}_{c}_animation" file = "{ident}_{c}.anim" }}' for c in clips)+'\n','utf8')
 gfx='pdxmesh = {\n name = "'+ident+'_mesh"\n file = "gfx/models/units/'+ident+'/'+ident+'.mesh"\n'+''.join(f' animation = {{ id = "{c}" type = "{ident}_{c}_animation" }}\n' for c in clips)+'}\n'
 state=[('idle','idle'),('idle','idle_look'),('idle','idle_shift'),('move','move'),('retreat','move'),('attack','attack'),('defend','attack'),('support_attack','attack'),('training','idle_look'),('death','death')]
 asset=f'entity = {{ name = "{ident}_entity" pdxmesh = "{ident}_mesh" scale = {scale}\n default_state = "idle"\n'
 for s,c in state:
  if c not in clips:c='idle'
  opts=' looping = no chance = 2' if s=='idle' else ''
  if s=='death':opts=' looping = no'
  asset+=f' state = {{ name = "{s}" animation = "{c}" animation_blend_time = 0.15{opts}\n'
  if c=='attack' and particle:
   for t in (.18,.38,.58):asset+=f' event = {{ time = {t} node = "{locator}" particle = "{particle}" keep_particle = yes sound = {{ soundeffect = "infantry_rifle_attack" }} }}\n'
  asset+=' }\n'
 asset+='}\n'
 return gfx,asset
def replace_definition(rel,name,new):
 out=STAGE/rel;original=out if out.exists() else ROOT/rel;text=original.read_text('utf-8-sig')
 nodes=parse(text);nodes=nodes[0].children if rel.endswith('.gfx') else nodes
 node=next(n for n in nodes if n.val('name')==name);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(patches(text,[(node.start,node.end,new)]),'utf8')
def save_source(ident,rig,obs):
 out=WORK/'source'/ident;out.mkdir(parents=True,exist_ok=True);select([rig]+obs)
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(out/(ident+'.blend')))
def render(ident,rig,clip,frame,scale=1):
 scene=bpy.context.scene;scene.frame_set(frame);bpy.context.view_layer.update()
 meshes=[o for o in scene.objects if o.type=='MESH' and not o.hide_render]
 deps=bpy.context.evaluated_depsgraph_get();pts=[]
 for ob in meshes:
  ev=ob.evaluated_get(deps);pts.extend(ev.matrix_world@Vector(p) for p in ev.bound_box)
 if not pts:return
 low=Vector(tuple(min(p[i] for p in pts) for i in range(3)));high=Vector(tuple(max(p[i] for p in pts) for i in range(3)));center=(low+high)/2;size=max(high-low)
 world=bpy.data.worlds.new('QA_world');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[1].default_value=.65
 added=[]
 for loc in ((1,-2,3),(-2,-1,1),(1,2,2)):
  light=bpy.data.lights.new('QA_light','AREA');light.energy=110*size*size;light.size=size*1.3;ob=bpy.data.objects.new('QA_light',light);scene.collection.objects.link(ob);ob.location=center+Vector(loc)*size;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler();added.append(ob)
 camd=bpy.data.cameras.new('QA_camera');cam=bpy.data.objects.new('QA_camera',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.type='ORTHO';camd.ortho_scale=size*1.32;cam.location=center+Vector((1.4,-2.8,1))*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();added.append(cam)
 scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16;scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 out=WORK/'previews';out.mkdir(exist_ok=True,parents=True);scene.render.filepath=str(out/(ident+'_'+clip+'.png'));bpy.ops.render.render(write_still=True)
 for ob in added:bpy.data.objects.remove(ob,do_unlink=True)
