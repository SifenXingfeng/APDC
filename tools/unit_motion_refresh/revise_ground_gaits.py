"""Replace only six custom ground walk clips; preserve all accepted meshes/other states."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
from gaits import *

reports=[]
for ident in GROUND_MODELS:
    bpy.ops.wm.open_mainfile(filepath=str(WORK/'source'/ident/(ident+'.blend')))
    scene=bpy.context.scene;scene.render.fps=30
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='POSE'
    obs=[o for o in bpy.data.objects if o.type=='MESH']
    rest={b.name:b.head_local.copy() for b in rig.data.bones};legs=[]
    for name,h in rest.items():
        if not name.endswith('_upper') or name[:-6]+'_foot' not in rest:continue
        lower=name[:-6]+'_lower';foot=name[:-6]+'_foot';k,a=rest[lower],rest[foot]
        axis=(a-h).normalized();pole=k-h-axis*(k-h).dot(axis)
        pole=Vector((0,-1,0)) if pole.length<.15 else pole.normalized()
        legs.append(dict(bones=[name,lower,foot],hip=h,knee=k,ankle=a,pole=pole))
    assign_alternating(legs);cfg=settings(ident)
    bob_function=lambda t:.025*math.sin(t*math.tau*2)
    crouch=reachable_body_offset(legs,cfg,bob_function)
    previous=bpy.data.actions.get(ident+'_move')
    if previous:bpy.data.actions.remove(previous)
    begin(rig,ident+'_move');prev={};max_error=0
    for frame in range(1,cfg['frames']+1):
        scene.frame_set(frame);clear_pose(rig);t=(frame-1)/(cfg['frames']-1)
        bob=crouch+bob_function(t);rig.pose.bones['hull'].location.z=bob
        for name in ('hair','cloak'):
            if name in rig.pose.bones:
                rig.pose.bones[name].rotation_quaternion=Euler((.035*math.sin(t*math.tau),.026*math.sin(t*math.tau+.6),0)).to_quaternion()
        bpy.context.view_layer.update()
        for leg in legs:
            y,z,contact=foot_path(t,leg['phase'],cfg['stride'],cfg['lift'],cfg['duty'])
            target=Vector(leg['ankle'])+Vector((0,y,z));set_chain(rig,leg,target,bob)
            max_error=max(max_error,(rig.pose.bones[leg['bones'][2]].matrix.translation-target).length)
        for b in rig.pose.bones:
            if b.name in prev and b.rotation_quaternion.dot(prev[b.name])<0:b.rotation_quaternion.negate()
            prev[b.name]=b.rotation_quaternion.copy()
        key_all(rig,frame)
    assert max_error<.015,(ident,'IK reach error',max_error)
    export_clip(rig,ident,'move',cfg['frames'])
    rig.animation_data.action=bpy.data.actions[ident+'_idle'];scene.frame_set(1);save_source(ident,rig,obs)
    reports.append({'id':ident,'settings':cfg,'body_crouch':crouch,'legs':[{k:list(v) if k in ('hip','knee','ankle','pole') else v for k,v in l.items()} for l in legs], 'maximum_ik_target_error':max_error})
    save_json(WORK/'gait_revision_authoring.json',reports)
    print('REVISED_GAIT',ident,len(legs),'IK error',max_error,flush=True)
