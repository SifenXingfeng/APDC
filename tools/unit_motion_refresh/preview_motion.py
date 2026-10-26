import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
for ident in ('APDC_ump_chibi','APDC_b2_aa02'):
 bpy.ops.wm.open_mainfile(filepath=str(WORK/'source'/ident/(ident+'.blend')));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.animation_data_clear();rig.data.pose_position='POSE';clear_pose(rig)
 io.import_animfile(str(ROOT/'gfx/models/units'/ident/(ident+'_move.anim')));scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
 points=[o.matrix_world@Vector(p) for o in scene.objects if o.type=='MESH' for p in o.bound_box];lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)/2;size=max(hi-lo)
 world=bpy.data.worlds.new('preview');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[1].default_value=.6
 for location in ((1,-2,3),(-2,-1,2),(1,2,3)):
  data=bpy.data.lights.new('light','AREA');data.energy=90*size*size;data.size=size*1.5;ob=bpy.data.objects.new('light',data);scene.collection.objects.link(ob);ob.location=center+Vector(location)*size;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
 bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.02));floor=bpy.context.object;mat=bpy.data.materials.new('floor');mat.diffuse_color=(.10,.12,.14,1);floor.data.materials.append(mat)
 data=bpy.data.cameras.new('camera');cam=bpy.data.objects.new('camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=size*1.30;cam.location=center+Vector((1.4,-3,1.0))*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16;scene.render.resolution_x=480;scene.render.resolution_y=480;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 out=WORK/'previews/frames'/ident;out.mkdir(parents=True,exist_ok=True)
 for frame in range(1,31,2):scene.frame_set(frame);scene.render.filepath=str(out/f'{frame:03}.png');bpy.ops.render.render(write_still=True)
 print('MOTION_FRAMES_COMPLETE',ident,flush=True)
