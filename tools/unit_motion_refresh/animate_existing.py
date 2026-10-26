"""Author multi-state motion on retained mechanical/character meshes with fixed knee poles."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
from gaits import assign_alternating,foot_path,settings
T=math.tau
selected=['APDC_b2_automaton','APDC_b2_multipod','APDC_b2_doomdog','APDC_b2_aa02','APDC_f1_multipod_artillery','APDC_f1_nyto_final','APDC_b2_goliath','APDC_b2_helicopter','APDC_f1_armed_helicopter']
catalog=sources();reports=[]
for ident in selected:
 print('BEGIN_MOTION',ident,flush=True);entry=catalog[ident];info=entry['info']
 bpy.ops.wm.open_mainfile(filepath=entry['blend']);scene=bpy.context.scene;scene.render.fps=30
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='POSE';obs=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
 for ob in list(bpy.data.objects):
  if ob not in obs+[rig] and ob.type in ('MESH','LIGHT','CAMERA'):bpy.data.objects.remove(ob,do_unlink=True)
 rest={b.name:b.head_local.copy() for b in rig.data.bones};legs=[]
 for name in rest:
  if not name.endswith('_upper'):continue
  stem=name[:-6];lower=stem+'_lower';foot=stem+'_foot'
  if lower not in rest or foot not in rest:continue
  h,k,a=rest[name],rest[lower],rest[foot];axis=(a-h).normalized();pole=k-h-axis*(k-h).dot(axis)
  # Fixed model-space pole. The previous solver recomputed its sign from the
  # moving target, so almost straight knees switched sides during the stride.
  if pole.length<.15:pole=Vector((0,-1,0))
  else:pole.normalize()
  legs.append({'bones':[name,lower,foot],'hip':h,'knee':k,'ankle':a,'pole':pole})
 if legs:assign_alternating(legs)
 flying='helicopter' in ident or 'goliath' in ident;nyto='nyto' in ident;heli='helicopter' in ident
 crouch=reachable_body_offset(legs,settings(ident),lambda t:.025*math.sin(t*T*2)) if legs and not flying else 0.
 clips=['idle','idle_look','idle_shift','move','attack','death'];checks=[]
 for clip in clips:
  frames=91 if clip.startswith('idle') else (61 if clip=='death' else 31)
  act=begin(rig,ident+'_'+clip);prev_quat={};min_bend=999;lowest=999
  for f in range(1,frames+1):
   scene.frame_set(f);clear_pose(rig);t=(f-1)/(frames-1);duration=(frames-1)/30
   bob=crouch+.025*math.sin(t*T*2) if clip=='move' else .014*math.sin(t*T)
   root=rig.pose.bones['root'];hull=rig.pose.bones['hull']
   if flying:
    height=4.5 if heli else 2.4;root.location.z=height+.13*math.sin(t*T)
    hull.rotation_quaternion=Euler((-.10 if clip=='move' else .025*math.sin(t*T),.035*math.sin(t*T),.04*math.sin(t*T))).to_quaternion()
   else:hull.location.z=bob
   if clip=='idle_look':
    for name in ('head','turret'):
     if name in rig.pose.bones:rig.pose.bones[name].rotation_quaternion=Euler((.035*math.sin(t*T),0,.24*math.sin(t*T))).to_quaternion()
    if not any(n in rig.pose.bones for n in ('head','turret')):hull.rotation_quaternion=Euler((0,.035*math.sin(t*T),.09*math.sin(t*T))).to_quaternion()
   if clip=='idle_shift':
    hull.rotation_quaternion=Euler((.025*math.sin(t*T),.035*math.sin(t*T),0)).to_quaternion()
    for name in ('left_arm','right_arm','left_upperarm','right_upperarm','left_claw','right_claw'):
     if name in rig.pose.bones:rig.pose.bones[name].rotation_quaternion=Euler((.09*math.sin(t*T),0,.06*math.sin(t*T))).to_quaternion()
   for name in ('hair','cloak'):
    if name in rig.pose.bones:rig.pose.bones[name].rotation_quaternion=Euler((.035*math.sin(t*T),.026*math.sin(t*T+.6),0)).to_quaternion()
   if heli:
    rig.pose.bones['rotor'].rotation_quaternion=Quaternion((0,0,1),t*duration*T*5)
    rig.pose.bones['tail_rotor'].rotation_quaternion=Quaternion((1,0,0),t*duration*T*7)
   if clip=='attack':
    recoil=sum(max(0,1-abs(t-a)/.065) for a in (.18,.38,.58))
    hull.location.y+=.045*recoil;hull.rotation_quaternion=Euler((.035*recoil,0,.035*math.sin(t*T))).to_quaternion()
    for name in ('gun','gun_left','gun_right'):
     if name in rig.pose.bones:rig.pose.bones[name].location.y=.12*recoil
    if nyto:
     swing=math.sin(math.pi*t)**2
     rig.pose.bones['chest'].rotation_quaternion=Euler((.10*swing,0,-.30*swing)).to_quaternion()
     rig.pose.bones['left_upperarm'].rotation_quaternion=Euler((-.35*swing,-.25*swing,.85*math.sin(t*T))).to_quaternion()
     rig.pose.bones['left_forearm'].rotation_quaternion=Euler((.32*swing,0,.15*swing)).to_quaternion()
    if 'goliath' in ident:
     root.location.y=-.55*math.sin(math.pi*t)**2;root.location.z-=.35*math.sin(math.pi*t)**2
     for name in ('left_arm','right_arm'):rig.pose.bones[name].rotation_quaternion=Euler((-.48*math.sin(math.pi*t)**2,0,0)).to_quaternion()
   bpy.context.view_layer.update()
   if not flying:
    for leg in legs:
     a=Vector(leg['ankle']);target=a.copy()
     if clip=='move':
      dy,dz,_=foot_path(t,leg['phase']);target.y+=dy;target.z+=dz
     elif clip=='attack':target.y-=.07*math.sin(math.pi*t)**2
     min_bend=min(min_bend,set_chain(rig,leg,target,bob));lowest=min(lowest,target.z)
   if clip=='death':
    q=min(1,t*1.5);q=q*q*(3-2*q)
    if flying:root.location.z=(4.5 if heli else 2.4)*(1-q);hull.rotation_quaternion=Euler((.35*q,.7*q,0)).to_quaternion()
    else:
     root.rotation_quaternion=Euler((math.pi*.43*q,0,.16*q)).to_quaternion();root.location.z=-.02*q
     hull.location.z-=.25*q
   # Keep quaternion signs continuous; exporter interpolation must never take
   # the long route through an equivalent negative quaternion.
   for b in rig.pose.bones:
    if b.name in prev_quat and b.rotation_quaternion.dot(prev_quat[b.name])<0:b.rotation_quaternion.negate()
    prev_quat[b.name]=b.rotation_quaternion.copy()
    assert all(math.isfinite(x) for row in b.matrix for x in row)
   key_all(rig,f)
  export_clip(rig,ident,clip,frames);checks.append({'clip':clip,'frames':frames,'fixed_pole_chains':len(legs) if not flying else 0,'airborne':flying})
 particle=None if nyto or 'goliath' in ident or ident=='APDC_b2_helicopter' else ('heavy_tank_attack_barrel_particle' if 'multipod' in ident or 'aa02' in ident else 'rifle_muzzle_particle')
 gfx,asset=ensure_asset(ident,clips,info.get('scale',.8),particle)
 pack='f1' if ident.startswith('APDC_f1') else 'b2'
 replace_definition('gfx/entities/APDC_'+pack+'_models.gfx',ident+'_mesh',gfx)
 replace_definition('gfx/entities/APDC_'+pack+'_models.asset',ident+'_entity',asset)
 rig.animation_data.action=bpy.data.actions[ident+'_idle'];scene.frame_set(1);save_source(ident,rig,obs)
 for clip,frame in [('move',9),('attack',15)]:
  rig.animation_data.action=bpy.data.actions[ident+'_'+clip];render(ident,rig,clip,frame)
 reports.append({'id':ident,'mesh_unchanged':True,'clips':checks,'smoking':False,'knee_pole_method':'fixed rest-plane direction projected onto hip-to-foot plane'})
 save_json(WORK/'motion_validation.json',reports)
 print('MOTION_COMPLETE',ident,flush=True)
