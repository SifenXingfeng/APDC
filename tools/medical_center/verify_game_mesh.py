"""Render the actual exported .mesh with its final DDS files, not source geometry."""
import argparse
import importlib
import json
import logging
from pathlib import Path
import sys
import types
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--exporter',required=True)
parser.add_argument('--project',required=True)
parser.add_argument('--delivery',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
root=Path(args.project); delivery=Path(args.delivery)
model=root/'gfx/models/buildings/APDC_medical_center'
bpy.ops.wm.open_mainfile(filepath=str(root/'art_source/medical_center/APDC_medical_center.blend'))
material=bpy.data.materials['APDC_medical_center_material']
for node in material.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        stem=Path(node.image.filepath).stem
        image=bpy.data.images.load(str(model/(stem+'.dds')),check_existing=False)
        image.colorspace_settings.name='sRGB' if stem.endswith('_diffuse') else 'Non-Color'
        node.image=image
for obj in list(bpy.data.objects):
    if obj.type=='MESH':
        bpy.data.objects.remove(obj,do_unlink=True)
package=types.ModuleType('io_pdx_mesh'); package.__path__=[args.exporter]
package.IO_PDX_LOG=logging.getLogger('io_pdx'); sys.modules[package.__name__]=package
sub=types.ModuleType('io_pdx_mesh.pdx_blender'); sub.__path__=[str(Path(args.exporter)/'pdx_blender')]
sys.modules[sub.__name__]=sub
backend=importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
data=importlib.import_module('io_pdx_mesh.pdx_data')
backend.create_material=lambda definition,mesh,texture_path:mesh.materials.append(material)
tree=data.read_meshfile(str(model/'APDC_medical_center.mesh'))
mesh=tree.find('object').find('APDC_medical_centerShape').find('mesh')
for field in ('diff','n','spec'):
    name=mesh.find('material').get(field)[0]
    assert (model/name).is_file(), name
backend.import_meshfile(str(model/'APDC_medical_center.mesh'),imp_mesh=True,imp_skel=False,imp_locs=False)
objects=[o for o in bpy.data.objects if o.type=='MESH']
assert len(objects)==1
objects[0].data.calc_loop_triangles()
assert len(objects[0].data.loop_triangles)==9814
scene=bpy.context.scene
scene.render.resolution_x=1400; scene.render.resolution_y=1100
scene.render.filepath=str(delivery/'医疗中心_游戏文件回读预览.png')
bpy.ops.render.render(write_still=True)
record_path=root/'art_source/medical_center/model_validation.json'
record=json.loads(record_path.read_text(encoding='utf-8'))
record['final_dds_and_mesh_rendered']=True
record['game_runtime_tested']=False
record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
(delivery/'文件验证记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('GAME_FILE_ROUNDTRIP_RENDER_VERIFIED',flush=True)
