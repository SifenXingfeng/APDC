"""Reimport final game mesh + DDS; test vanilla clips and render posed previews."""
import argparse
import importlib
import json
import logging
import math
from pathlib import Path
import re
import sys
import types
import bpy
from mathutils import Vector, Matrix

parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True);parser.add_argument('--exporter',required=True)
parser.add_argument('--delivery',required=True);parser.add_argument('--quick',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT=Path(args.project);SOURCE=ROOT/'art_source/penguin_infantry';MODEL=ROOT/'gfx/models/units/APDC_penguin'
DELIVERY=Path(args.delivery);UNITS=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV/gfx/models/units')
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[args.exporter];pkg.IO_PDX_LOG=logging.getLogger('io_pdx');sys.modules[pkg.__name__]=pkg
sub=types.ModuleType('io_pdx_mesh.pdx_blender');sub.__path__=[str(Path(args.exporter)/'pdx_blender')];sys.modules[sub.__name__]=sub
backend=importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'APDC_penguin.blend'))
material=bpy.data.materials['APDC_penguin_material']
for node in material.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        image=bpy.data.images.load(str(MODEL/(Path(node.image.filepath).stem+'.dds')),check_existing=False)
        image.colorspace_settings.name='sRGB' if image.name.startswith('APDC_penguin_diffuse') else 'Non-Color'
        node.image=image
for obj in list(bpy.data.objects):
    if obj.type in ('MESH','ARMATURE','EMPTY'):bpy.data.objects.remove(obj,do_unlink=True)
backend.create_material=lambda definition,mesh,texture_path:mesh.materials.append(material)
backend.import_meshfile(str(MODEL/'APDC_penguin.mesh'),imp_mesh=True,imp_skel=True,imp_locs=True)
body=next(o for o in bpy.data.objects if o.type=='MESH')
rig=next(m.object for m in body.modifiers if m.type=='ARMATURE')
scene=bpy.context.scene
record=json.loads((SOURCE/'validation.json').read_text(encoding='utf-8'))
assert len(rig.data.bones)==33
tree=pdx.read_meshfile(str(MODEL/'APDC_penguin.mesh'))
original=pdx.read_meshfile(str(UNITS/'GER_infantry.mesh'))
assert [b.tag for b in tree.find('object/APDC_penguinShape/skeleton')]==[b.tag for b in original.find('object/GER_infantryShape/skeleton')]
mapping=(ROOT/'gfx/entities/APDC_penguin_infantry.gfx').read_text()
animation_types=set(re.findall(r'type\s*=\s*"([^"]+)"',mapping))
registry=(MODEL/'animations/animation.asset').read_text(encoding='utf-8-sig')
animation_files={m[0]:m[1] for m in re.findall(r'animation\s*=\s*\{\s*name\s*=\s*"([^"]+)"\s*file\s*=\s*"([^"]+)"',registry)}
assert animation_types<=animation_files.keys(),animation_types-animation_files.keys()
filenames=sorted(set(animation_files[k] for k in animation_types))
rig_names={b.name for b in rig.data.bones}
for filename in filenames:
    info=pdx.read_meshfile(str(MODEL/'animations'/filename)).find('info')
    assert {b.tag for b in info}<=rig_names,filename
record['animation_files_resolved']=len(filenames)
record['animation_bone_compatibility']=True

def clip(filename):
    rig.animation_data_clear();rig.data.pose_position='POSE'
    if not filename.startswith('APDC_'):filename='APDC_'+filename
    backend.import_animfile(str(MODEL/'animations'/filename))
    scene.frame_set(scene.frame_start);bpy.context.view_layer.update()

def geometry_snapshot(frame):
    scene.frame_set(frame);bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
    coords=[tuple(v.co) for v in mesh.vertices]
    assert all(math.isfinite(c) for p in coords for c in p)
    span=[max(p[i] for p in coords)-min(p[i] for p in coords) for i in range(3)]
    assert max(span)<30,(frame,span)
    ev.to_mesh_clear();return {'frame':frame,'dimensions':span}

tested=[]
if not args.quick:
    for index,filename in enumerate(filenames):
        clip(filename)
        frames=sorted(set([scene.frame_start,scene.frame_start+(scene.frame_end-scene.frame_start)//4,
                           (scene.frame_start+scene.frame_end)//2,scene.frame_start+(scene.frame_end-scene.frame_start)*3//4,scene.frame_end]))
        tested.append({'file':filename,'samples':[geometry_snapshot(frame) for frame in frames]})
        print('CLIP_CHECK '+str(index+1)+'/'+str(len(filenames))+' '+filename,flush=True)
    record['sampled_animation_checks']=tested

# Preview attachments use the same four nodes as the cloned vanilla rifle entity.
def weapon_material(definition,mesh,texture_path):
    mat=bpy.data.materials.new('Preview_vanilla_weapon');mat.use_nodes=True
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(Path(texture_path)/definition.diff[0]))
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.4;mesh.materials.append(mat)
backend.create_material=weapon_material
old=set(bpy.data.objects)
backend.import_meshfile(str(UNITS/'GER_infantry_weapon_k98_rifle.mesh'),imp_mesh=True,imp_skel=False,imp_locs=False)
template=next(o for o in set(bpy.data.objects)-old if o.type=='MESH')
weapons=[]
for index,node in enumerate(['Right_Hand_node','Left_Hand_node','mid_back_node','Root_node_2']):
    obj=template if index==0 else template.copy()
    if index:scene.collection.objects.link(obj)
    obj.name='Preview_weapon_'+node;weapons.append((obj,node))
def attachments():
    for obj,node in weapons:obj.matrix_world=rig.matrix_world@rig.pose.bones[node].matrix

previews=[('待机','GER_infantry_idle_rifle.anim',1),('行军','GER_infantry_moving_rifle.anim',12),
          ('射击','GER_infantry_attack_stand_rifle.anim',20),('蹲姿','GER_infantry_attack_crouch_rifle.anim',20),
          ('死亡','GER_infantry_death_rifle.anim',-1),('训练','GER_infantry_jumping_jacks.anim',15)]
camera=scene.camera;camera.location=(10,-17,10)
camera.rotation_euler=(Vector((0,0,3.6))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=900;scene.render.resolution_y=1050;scene.cycles.samples=24
for label,filename,frame in previews:
    clip(filename);scene.frame_set(scene.frame_end if frame<0 else min(frame,scene.frame_end));bpy.context.view_layer.update();attachments()
    geometry_snapshot(scene.frame_current)
    camera.location=(10,-17,10)
    camera.rotation_euler=(Vector((0,0,3.6))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=10.3
    if label=='死亡':
        # A falling unit moves away from its standing origin. Frame the actual
        # posed bounds so the inspection render does not crop the head/weapon.
        ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        points=[ev.matrix_world@vertex.co for vertex in me.vertices];ev.to_mesh_clear()
        center=Vector([(min(p[i] for p in points)+max(p[i] for p in points))*.5 for i in range(3)])
        camera.location=center+Vector((10,-17,9))
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update();inverse=camera.matrix_world.inverted()
        projected=[inverse@point for point in points]
        width=max(p.x for p in projected)-min(p.x for p in projected)
        height=max(p.y for p in projected)-min(p.y for p in projected)
        camera.data.ortho_scale=max(height,width*scene.render.resolution_y/scene.render.resolution_x)*1.35
    scene.render.filepath=str(DELIVERY/('企鹅步兵_'+label+'_游戏文件回读.png'))
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_READY '+label,flush=True)
clip('GER_infantry_idle_rifle.anim');attachments()
camera.data.ortho_scale=10.3
scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.cycles.samples=48
scene.render.filepath=str(DELIVERY/'企鹅步兵_最终预览.png');bpy.ops.render.render(write_still=True)
record['mesh_and_final_dds_reimported']=True
record['posed_previews_from_game_files']=[label for label,_,_ in previews]
record['game_runtime_tested']=False
(SOURCE/'validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(DELIVERY/'文件与动作验证记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('PENGUIN_ROUNDTRIP_COMPLETE '+json.dumps({'clips_resolved':len(filenames),'clips_sampled':len(tested),'game_runtime_tested':False}),flush=True)
