"""Open editable sources in idle; keep weapon preview props bone-attached."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
for path in (WORK/'source').glob('*/*.blend'):
 ident=path.stem;bpy.ops.wm.open_mainfile(filepath=str(path));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
 if bpy.data.actions.get(ident+'_idle'):
  rig.animation_data.action=bpy.data.actions[ident+'_idle'];rig.data.pose_position='POSE';bpy.context.scene.frame_set(1)
 if ident in ('APDC_r6_tactical_doll','APDC_r6_lyuba'):
  props=sorted([o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(ident+'_weapon')],key=lambda o:o.name)
  for prop,bone in zip(props,('Right_Hand_node','Left_Hand_node','mid_back_node','Root_node_2')):
   prop.hide_render=False;prop.hide_set(False);prop.matrix_world=Matrix.Identity(4)
   for con in list(prop.constraints):prop.constraints.remove(con)
   con=prop.constraints.new('COPY_TRANSFORMS');con.target=rig;con.subtarget=bone;con.target_space='WORLD';con.owner_space='WORLD'
 bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('EDITABLE_SOURCES_TIDIED',flush=True)
