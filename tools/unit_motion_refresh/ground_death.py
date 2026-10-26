"""Keep authored falls above the terrain, verified on every exported frame."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
scope=json.loads((WORK/'scope.json').read_text('utf8'));results=[];ids=scope['existing_motion_models']+scope['new_chibi']
if '--only' in sys.argv:
 selected=set(sys.argv[sys.argv.index('--only')+1].split(','));ids=[n for n in ids if n in selected]
 results=[r for r in json.loads((WORK/'death_ground_validation.json').read_text('utf8')) if r['id'] not in selected]
for ident in ids:
 bpy.ops.wm.open_mainfile(filepath=str(WORK/'source'/ident/(ident+'.blend')))
 rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');obs=[o for o in bpy.data.objects if o.type=='MESH'];rig.data.pose_position='POSE'
 rig.animation_data_clear();clear_pose(rig);anim=STAGE/'gfx/models/units'/ident/(ident+'_death.anim');io.import_animfile(str(anim));rig.animation_data.action.name=ident+'_death_grounded';scene=bpy.context.scene;end=scene.frame_end
 corrections=[]
 for f in range(1,end+1):
  scene.frame_set(f);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();minimum=min((o.evaluated_get(deps).matrix_world@Vector(p)).z for o in obs for p in o.evaluated_get(deps).bound_box)
  corrections.append(max(0,-minimum)+.004)
 for f,c in enumerate(corrections,1):
  scene.frame_set(f);root=rig.pose.bones['root'];root.location.z+=c;root.keyframe_insert('location',frame=f,group=root.name)
 export_clip(rig,ident,'death',end)
 # Fresh binary import verifies the exported root channel, not just authoring data.
 rig.animation_data_clear();clear_pose(rig);io.import_animfile(str(anim));minimum=999
 for f in range(1,end+1):
  scene.frame_set(f);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();height=min((o.evaluated_get(deps).matrix_world@Vector(p)).z for o in obs for p in o.evaluated_get(deps).bound_box);minimum=min(minimum,height)
 assert minimum>=-.01,(ident,minimum)
 render(ident,rig,'binary_death',end)
 if bpy.data.actions.get(ident+'_idle'):rig.animation_data.action=bpy.data.actions[ident+'_idle'];scene.frame_set(1)
 save_source(ident,rig,obs);results.append({'id':ident,'minimum_height':minimum,'frames_checked':end,'animation_sha256':sha(anim),'max_vertical_correction':max(corrections)})
 save_json(WORK/'death_ground_validation.json',results);print('DEATH_GROUNDED',ident,flush=True)
