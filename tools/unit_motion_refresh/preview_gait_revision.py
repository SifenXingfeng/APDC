"""Render exported runtime mesh/animation with world-space ground references."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
from gaits import settings

def material(definition,mesh,directory):
    mat=bpy.data.materials.new(definition.diff[0]);mat.use_nodes=True
    node=mat.node_tree.nodes.new('ShaderNodeTexImage')
    rel=Path('gfx/models/units')/Path(directory).name/definition.diff[0]
    path=STAGE/rel if (STAGE/rel).exists() else ROOT/rel
    im=bpy.data.images.load(str(path));im.colorspace_settings.name='sRGB';node.image=im
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.67
    mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
io.create_material=material
selected=['APDC_ump_chibi','APDC_b2_multipod','APDC_b2_aa02']
if '--only' in sys.argv:selected=sys.argv[sys.argv.index('--only')+1].split(',')
metadata=[]
for ident in selected:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rel=Path('gfx/models/units')/ident/(ident+'.mesh');path=STAGE/rel if (STAGE/rel).exists() else ROOT/rel
    io.import_meshfile(str(path),imp_mesh=True,imp_skel=True,imp_locs=False)
    imported=set(bpy.data.objects);rig=next(o for o in imported if o.type=='ARMATURE')
    io.import_animfile(str(STAGE/'gfx/models/units'/ident/(ident+'_move.anim')))
    scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
    end=scene.frame_end;cfg=settings(ident)
    assembly=bpy.data.objects.new('World_motion_MINUS_Y',None);scene.collection.objects.link(assembly)
    for ob in imported:
        if ob.parent not in imported:
            matrix=ob.matrix_world.copy();ob.parent=assembly;ob.matrix_world=matrix
    points=[o.matrix_world@Vector(p) for o in imported if o.type=='MESH' for p in o.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)));center=(lo+hi)/2;size=max(hi-lo)
    scene.world=bpy.data.worlds.new('Grounded_preview');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
    lights=[]
    for location in ((1,-2,3),(-2,-1,2),(1,2,3)):
        data=bpy.data.lights.new('light','AREA');data.energy=90*size*size;data.size=size*1.5;ob=bpy.data.objects.new('light',data);scene.collection.objects.link(ob);ob.location=center+Vector(location)*size;ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler();lights.append((ob,ob.location.copy()))
    bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.005));floor=bpy.context.object
    mat=bpy.data.materials.new('stationary_world_checker');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
    geo=nodes.new('ShaderNodeNewGeometry');checker=nodes.new('ShaderNodeTexChecker');checker.inputs['Color1'].default_value=(.16,.20,.24,1);checker.inputs['Color2'].default_value=(.22,.27,.31,1);checker.inputs['Scale'].default_value=1.5
    links.new(geo.outputs['Position'],checker.inputs['Vector']);links.new(checker.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color']);floor.data.materials.append(mat)
    data=bpy.data.cameras.new('camera');cam=bpy.data.objects.new('camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=size*1.38
    cam.location=center+Vector((2.8,-1.8,1.2))*size;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();camera_origin=cam.location.copy()
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.eevee.taa_render_samples=16;scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    out=WORK/'previews/gait_revision_frames'/ident;out.mkdir(parents=True,exist_ok=True)
    # Two cycles at actual 30 fps, camera follows -Y, fixed checker makes forward
    # progress/ground contacts visible. Sample every other frame for a 15 fps GIF.
    frame_files=[]
    for step in range(0,(end-1)*2,2):
        scene.frame_set(1+step%(end-1));distance=step/(end-1)*cfg['stride']/cfg['duty'];offset=Vector((0,-distance,0))
        assembly.location=offset;cam.location=camera_origin+offset
        for light,origin in lights:light.location=origin+offset
        scene.render.filepath=str(out/f'{step:03}.png');bpy.ops.render.render(write_still=True);frame_files.append(str(out/f'{step:03}.png'))
    metadata.append({'id':ident,'frames':frame_files,'duration_ms':67,'runtime_mesh_sha256':sha(path),'runtime_animation_sha256':sha(STAGE/'gfx/models/units'/ident/(ident+'_move.anim'))})
    print('GROUNDED_PREVIEW_DONE',ident,flush=True)
save_json(WORK/'previews/gait_revision_frames.json',metadata)
