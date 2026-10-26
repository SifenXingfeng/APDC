"""Build the APDC medical center with Blender 4.2 in background mode.

Usage: blender --background --factory-startup --python build_medical_center.py --
       --exporter PATH/TO/io_pdx_mesh --project PATH/TO/APDC --delivery PATH
Creates genuine Clausewitz .mesh, a reusable .blend, procedural texture sources,
and renders. finish_medical_center.py converts textures to DDS and makes UI icons.
No external photograph is projected onto the model, and no text/logos are built.
"""
import argparse
import importlib
import json
import logging
import math
from pathlib import Path
import random
import sys
import types

import bpy
import bmesh
import numpy as np
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--exporter', required=True)
parser.add_argument('--project', required=True)
parser.add_argument('--delivery', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
project = Path(args.project)
delivery = Path(args.delivery)
model_dir = project / 'gfx/models/buildings/APDC_medical_center'
source_dir = project / 'art_source/medical_center'
for directory in (delivery, model_dir, source_dir):
    directory.mkdir(parents=True, exist_ok=True)

# Load only the upstream export backend, without its GUI, updater or preferences.
package = types.ModuleType('io_pdx_mesh')
package.__path__ = [str(Path(args.exporter))]
package.IO_PDX_LOG = logging.getLogger('io_pdx')
sys.modules['io_pdx_mesh'] = package
subpackage = types.ModuleType('io_pdx_mesh.pdx_blender')
subpackage.__path__ = [str(Path(args.exporter) / 'pdx_blender')]
sys.modules[subpackage.__name__] = subpackage
exporter = importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
pdx_data = importlib.import_module('io_pdx_mesh.pdx_data')

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0

# One atlas and one draw-call material. No alpha-blended glass: game-safe opaque
# architectural glazing uses colour/specularity, like vanilla building textures.
palette = [(218,219,212),(174,181,180),(126,143,153),(66,111,143),
           (37,73,95),(110,156,180),(29,39,46),(93,100,101),
           (153,153,142),(48,90,110),(48,61,66),(181,194,200),
           (200,207,207),(76,119,142),(139,169,179),(222,220,207)]
rng = np.random.default_rng(4909)
dim, tile = 1024, 256
diffuse = np.ones((dim,dim,4), dtype=np.float32)
normal = np.ones_like(diffuse)
specular = np.ones_like(diffuse)
normal[:] = (0.5,0.5,0.0,0.5)  # HOI4: X=G, Y=-A, B=emissive (zero).
yy,xx = np.mgrid[0:tile,0:tile]
for slot, colour in enumerate(palette):
    row, col = divmod(slot,4)
    noise = rng.normal(0, 0.003 if slot not in (7,8) else 0.015, (tile,tile,1))
    rgb = np.broadcast_to(np.array(colour,dtype=np.float32)/255, (tile,tile,3)).copy()
    rgb += noise
    if slot in (3,4,5,9,13,14):
        # Restrained sky/room reflection, not a photograph or lettering.
        gradient = (yy/tile-0.5)*0.045
        reflection = 0.055*np.exp(-((xx/tile-0.37-(yy/tile)*0.12)/0.105)**2)
        rgb += (gradient+reflection)[:,:,None]
        gloss, strength, metal = 0.77, 0.8, 0.03
    elif slot in (2,11):
        gloss, strength, metal = 0.57, 0.7, 0.75
    else:
        gloss, strength, metal = 0.2, 0.28, 0.0
    if slot == 10:
        rgb[(yy % 18) < 5] *= 0.48
    target = np.s_[row*tile:(row+1)*tile, col*tile:(col+1)*tile]
    diffuse[target][:,:,:3] = np.clip(rgb,0,1)
    specular[target] = (0.0,strength,metal,gloss)

def make_image(name, values, data=False):
    image = bpy.data.images.new(name, width=dim, height=dim, alpha=True)
    if data:
        image.colorspace_settings.name = 'Non-Color'
    image.pixels.foreach_set(values.ravel())
    image.filepath_raw = str(source_dir / (name+'.png'))
    image.file_format = 'PNG'
    image.save()
    return image

images = {'diffuse': make_image('APDC_medical_center_diffuse',diffuse),
          'normal': make_image('APDC_medical_center_normal',normal,True),
          'specular': make_image('APDC_medical_center_specular',specular,True)}
material = bpy.data.materials.new('APDC_medical_center_material')
material['shader'] = 'PdxMeshAdvancedSnow'
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
bsdf = nodes.get('Principled BSDF')
tex = nodes.new('ShaderNodeTexImage'); tex.image = images['diffuse']
links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
props = nodes.new('ShaderNodeTexImage'); props.image = images['specular']
split = nodes.new('ShaderNodeSeparateColor')
links.new(props.outputs['Color'],split.inputs['Color'])
links.new(split.outputs['Green'],bsdf.inputs['Specular IOR Level'])
links.new(split.outputs['Blue'],bsdf.inputs['Metallic'])
invert = nodes.new('ShaderNodeMath'); invert.operation='SUBTRACT'; invert.inputs[0].default_value=1
links.new(props.outputs['Alpha'],invert.inputs[1]); links.new(invert.outputs[0],bsdf.inputs['Roughness'])
# Flat tangent normals for this geometry-led asset. Link the packed normal for
# exporter discovery and decode it correctly in Blender as well.
normtex = nodes.new('ShaderNodeTexImage'); normtex.image=images['normal']
normsplit=nodes.new('ShaderNodeSeparateColor'); links.new(normtex.outputs['Color'],normsplit.inputs['Color'])
normcombine=nodes.new('ShaderNodeCombineColor'); normcombine.inputs['Blue'].default_value=1
links.new(normsplit.outputs['Green'],normcombine.inputs['Red'])
links.new(normtex.outputs['Alpha'],normcombine.inputs['Green'])
normalmap=nodes.new('ShaderNodeNormalMap'); links.new(normcombine.outputs[0],normalmap.inputs['Color'])
links.new(normalmap.outputs[0],bsdf.inputs['Normal'])

class Builder:
    def __init__(self):
        self.vertices=[]; self.faces=[]; self.styles=[]; self.smooth=[]; self.parts={}
    def face(self, vertices, style=0, smooth=False):
        start=len(self.vertices)
        self.vertices.extend(vertices)
        self.faces.append(tuple(range(start,start+len(vertices))))
        self.styles.append(style); self.smooth.append(smooth)
    def box(self, x0,x1,y0,y1,z0,z1,style=0):
        p=[(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
           (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
        for face in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.face([p[i] for i in face],style)
    def prism(self, outline,z0,z1,style=0):
        self.face([(x,y,z0) for x,y in reversed(outline)],style)
        self.face([(x,y,z1) for x,y in outline],style)
        for i,(x,y) in enumerate(outline):
            u,v=outline[(i+1)%len(outline)]
            self.face([(x,y,z0),(u,v,z0),(u,v,z1),(x,y,z1)],style)
    def rounded(self,x0,x1,y0,y1,z0,z1,r=0.8,style=0):
        self.prism(rounded_points(x0,x1,y0,y1,r),z0,z1,style)
    def front_frame(self, outer,inner,y0,y1,style=0):
        a=rounded_points(*outer); b=rounded_points(*inner)
        assert len(a)==len(b)
        for i in range(len(a)):
            j=(i+1)%len(a)
            self.face([(a[i][0],y0,a[i][1]),(a[j][0],y0,a[j][1]),(b[j][0],y0,b[j][1]),(b[i][0],y0,b[i][1])],style)
            self.face([(b[i][0],y1,b[i][1]),(b[j][0],y1,b[j][1]),(a[j][0],y1,a[j][1]),(a[i][0],y1,a[i][1])],style)
            self.face([(a[j][0],y0,a[j][1]),(a[i][0],y0,a[i][1]),(a[i][0],y1,a[i][1]),(a[j][0],y1,a[j][1])],style)
            self.face([(b[i][0],y0,b[i][1]),(b[j][0],y0,b[j][1]),(b[j][0],y1,b[j][1]),(b[i][0],y1,b[i][1])],style)

def rounded_points(x0,x1,y0,y1,r,steps=8):
    r=min(r,(x1-x0)/2,(y1-y0)/2)
    result=[]
    for cx,cy,angle in ((x1-r,y0+r,-90),(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180)):
        for i in range(steps+1):
            a=math.radians(angle+i*90/steps)
            result.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    return result

geo=Builder()
random.seed(4909)

def windows(x0,x1,y,z0,z1,columns,back=False):
    step=(x1-x0)/columns
    for column in range(columns):
        lo=x0+column*step+0.045; hi=x0+(column+1)*step-0.045
        style=random.choice([3,3,3,5,13,14])
        points=[(lo,y,z0),(hi,y,z0),(hi,y,z1),(lo,y,z1)]
        geo.face(points[::-1] if back else points,style)
        skin_y=y+(0.055 if back else -0.055)
        mullion=[(lo-0.05,skin_y,z0),(lo+0.015,skin_y,z0),(lo+0.015,skin_y,z1),(lo-0.05,skin_y,z1)]
        geo.face(mullion[::-1] if back else mullion,11)
        # Internal lower transom and a thin dark spandrel.
        transom=[(lo,skin_y,z0+0.65),(hi,skin_y,z0+0.65),(hi,skin_y,z0+0.7),(lo,skin_y,z0+0.7)]
        geo.face(transom[::-1] if back else transom,2)
    geo.box(x0,x1,y-0.055,y+0.055,z0-0.12,z0,6)

def side_windows(x,y0,y1,z0,z1,columns,left=False):
    step=(y1-y0)/columns
    for c in range(columns):
        lo=y0+c*step+0.04; hi=y0+(c+1)*step-0.04
        points=[(x,lo,z0),(x,hi,z0),(x,hi,z1),(x,lo,z1)]
        geo.face(points[::-1] if left else points,random.choice([3,4,13]))
        skin_x=x+(-0.055 if left else 0.055)
        mullion=[(skin_x,lo-0.04,z0),(skin_x,lo+0.015,z0),(skin_x,lo+0.015,z1),(skin_x,lo-0.04,z1)]
        geo.face(mullion[::-1] if left else mullion,11)

# Raised foundation and three shallow entrance steps, without surroundings.
geo.rounded(-22,20,-10.3,12.2,0,0.48,0.8,8)
for i in range(3):
    geo.box(-6.5,4.5,-12+i*0.55,-9.8,0,0.14+i*0.13,8)

# Ground-floor shared entrance/podium, fully modelled on all four sides.
geo.rounded(-21,19.4,-9.2,11.2,0.48,5.2,0.7,4)
windows(-20.2,18.5,-9.22,0.68,4.83,26)
windows(-20.2,18.5,11.22,0.68,4.83,26,True)
side_windows(-21.02,-8.5,10.5,0.7,4.8,13,True)
side_windows(19.42,-8.5,10.5,0.7,4.8,13)
geo.rounded(-21.5,19.9,-9.65,11.7,4.92,5.6,0.9,0)
geo.box(-6.2,4.2,-11.1,-8.8,4.5,4.8,11)
for x in (-5.8,3.8):
    geo.box(x-0.1,x+0.1,-10.8,-10.6,0.5,4.5,11)
for x in (-3.0,-1.45,0.1):
    geo.box(x,x+1.42,-9.4,-9.27,0.6,3.45,9)
    geo.box(x+1.30,x+1.34,-9.44,-9.38,1.5,2.1,11)

# The lower, setback left wing: horizontal white bands and dense ribbon glazing.
geo.rounded(-21,-1.3,-1.7,11.1,5.6,29.3,0.65,4)
for floor in range(7):
    z=5.6+floor*3.35
    geo.rounded(-21.4,-0.95,-2.05,11.5,z,z+0.66,0.8,0)
    windows(-20.65,-1.6,-1.73,z+0.8,z+3.1,16)
    windows(-20.65,-1.6,11.13,z+0.8,z+3.1,16,True)
    side_windows(-21.03,-1.0,10.4,z+0.8,z+3.1,9,True)
geo.rounded(-21.45,-0.95,-2.1,11.55,29.15,29.85,0.85,0)
geo.rounded(-20.85,-1.55,-1.5,10.95,29.85,29.92,0.5,7)

# Three-storey right-hand podium, with a large curved white perimeter frame.
geo.rounded(-2.2,19.0,-9.0,9.9,5.6,18.6,1.4,4)
for floor in range(3):
    z=5.65+floor*4.17
    windows(-1.25,17.35,-9.025,z+0.65,z+3.78,14)
    windows(-1.3,17.5,9.925,z+0.6,z+3.8,14,True)
    side_windows(19.025,-7.6,8.5,z+0.65,z+3.78,11)
    if floor:
        geo.rounded(-2.65,13.8,-9.65,10.2,z,z+0.74,1.25,0)
geo.front_frame((-2.85,19.7,5.15,18.9,1.85),(-1.6,17.55,6.15,17.68,1.0),-9.65,-9.0,0)
geo.rounded(-2.55,19.45,-9.35,10.1,18.35,19.05,1.5,0)

# Main tower. The broad blank right-hand fascia replaces all photographed text.
geo.rounded(-1.45,18.0,-6.95,9.0,18.7,44.3,1.55,4)
for floor in range(7):
    z=19.1+floor*3.45
    windows(-0.65,16.15,-6.975,z+0.65,z+3.1,13)
    windows(-0.65,16.7,9.025,z+0.5,z+3.08,13,True)
    side_windows(-1.475,-5.5,7.5,z+0.65,z+3.08,10,True)
    side_windows(18.025,-5.5,7.5,z+0.65,z+3.08,10)
    # The projecting bands stop short of the white right-hand upright.
    geo.rounded(-1.95,12.85,-7.62,9.35,z,z+0.68,1.28,0)
    geo.box(12.75,16.7,-7.12,-6.97,z+0.06,z+0.21,11)
geo.front_frame((-2.0,19.2,18.35,45.1,2.0),(-0.85,16.55,19.35,43.55,1.2),-7.56,-6.92,0)
geo.box(17.2,18.4,-5.5,8.1,19,44.0,1)
geo.rounded(-2.0,19.2,-7.55,9.65,44.45,45.1,1.8,0)
geo.rounded(-1.3,18.5,-6.85,8.95,45.1,45.17,1.2,7)

# Roof access housings and restrained mechanical plant, visible from map view.
def plant(x,y,z,w=4.4,d=2.5):
    geo.box(x-w/2,x+w/2,y-d/2,y+d/2,z,z+1.2,1)
    geo.box(x-w/2+0.12,x+w/2-0.12,y-d/2-0.025,y-d/2-0.01,z+0.2,z+0.95,10)
    for c in (-0.24,0.24):
        points=[(x+c*w+0.67*math.cos(a*math.tau/16),y+0.67*math.sin(a*math.tau/16)) for a in range(16)]
        geo.prism(points,z+1.2,z+1.3,6)
        for k in range(3):
            angle=k*math.tau/3
            geo.face([(x+c*w,y,z+1.31),(x+c*w+0.57*math.cos(angle),y+0.57*math.sin(angle),z+1.31),
                      (x+c*w+0.35*math.cos(angle+0.85),y+0.35*math.sin(angle+0.85),z+1.31)],2)
plant(7.0,4.2,45.17)
plant(-14,5.7,29.92)
plant(-7.6,5.7,29.92)
geo.box(1.0,4.6,3.8,7.7,45.17,47.0,1)
geo.box(0.8,4.8,3.6,7.9,47.0,47.25,0)
geo.box(1.95,3.3,3.77,3.79,45.3,46.6,10)

# A single static mesh, scaled to world-map building units before export.
scale=0.14
mesh=bpy.data.meshes.new('APDC_medical_centerShape')
mesh.from_pydata([tuple(c*scale for c in p) for p in geo.vertices],[],geo.faces)
mesh.materials.append(material)
mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for polygon,style,smooth in zip(mesh.polygons,geo.styles,geo.smooth):
    polygon.use_smooth=smooth
    dominant=max(range(3),key=lambda a:abs(polygon.normal[a]))
    axes=[i for i in range(3) if i!=dominant]
    coordinates=[(mesh.vertices[mesh.loops[i].vertex_index].co[axes[0]],mesh.vertices[mesh.loops[i].vertex_index].co[axes[1]]) for i in polygon.loop_indices]
    lo=[min(p[a] for p in coordinates) for a in (0,1)]
    hi=[max(p[a] for p in coordinates) for a in (0,1)]
    row,col=divmod(style,4)
    for loop_index,p in zip(polygon.loop_indices,coordinates):
        normalized=[(p[a]-lo[a])/max(hi[a]-lo[a],1e-8) for a in (0,1)]
        uv.data[loop_index].uv=((col+0.035+0.93*normalized[0])/4,(row+0.035+0.93*normalized[1])/4)
obj=bpy.data.objects.new('APDC_medical_center',mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
triangulated=bmesh.new()
triangulated.from_mesh(mesh)
bmesh.ops.triangulate(triangulated,faces=list(triangulated.faces))
triangulated.to_mesh(mesh)
triangulated.free()
mesh.calc_loop_triangles()
assert len(mesh.loop_triangles)<24000, len(mesh.loop_triangles)
assert len(mesh.vertices)<65535

# Export with texture basenames ending in DDS; the final conversion is lossless.
for key,image in images.items():
    image.filepath=str(model_dir / ('APDC_medical_center_'+key+'.dds'))
mesh_path=model_dir / 'APDC_medical_center.mesh'
exporter.export_meshfile(str(mesh_path),exp_mesh=True,exp_skel=False,exp_locs=False,exp_selected=True)
parsed=pdx_data.read_meshfile(str(mesh_path))
shape=parsed.find('object').find('APDC_medical_centerShape')
assert shape is not None
submeshes=shape.findall('mesh')
assert len(submeshes)==1
part=submeshes[0]
assert len(part.get('tri'))==len(mesh.loop_triangles)*3
assert all(math.isfinite(float(v)) for attribute in ('p','n','ta','u0') for v in part.get(attribute))
assert part.find('material').get('shader')==['PdxMeshAdvancedSnow']
exported_vertices=len(part.get('p'))//3
assert exported_vertices<65535

# Confirm independent importer reconstructs the .mesh coordinate system and UVs.
# Use the same preview material to avoid old addon GUI shader constructors.
def import_material(pdx_material, imported_mesh, texture_path):
    imported_mesh.materials.append(material)
exporter.create_material=import_material
before=set(bpy.data.objects)
exporter.import_meshfile(str(mesh_path),imp_mesh=True,imp_skel=False,imp_locs=False,join_materials=True)
imported=[o for o in set(bpy.data.objects)-before if o.type=='MESH']
assert imported
original_bounds=np.array([obj.matrix_world@Vector(corner) for corner in obj.bound_box])
roundtrip_bounds=np.concatenate([np.array([o.matrix_world@Vector(corner) for corner in o.bound_box]) for o in imported])
assert np.allclose(original_bounds.min(axis=0),roundtrip_bounds.min(axis=0),atol=0.0001)
assert np.allclose(original_bounds.max(axis=0),roundtrip_bounds.max(axis=0),atol=0.0001)
for imported_obj in imported:
    bpy.data.objects.remove(imported_obj,do_unlink=True)
for key,image in images.items():
    image.filepath=str(source_dir / ('APDC_medical_center_'+key+'.png'))
    image.pack()

scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=40
scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=True
scene.world.color=(0.34,0.34,0.34)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.66,0.75,0.84,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.5
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'

def point(object_,at):
    object_.rotation_euler=(Vector(at)-object_.location).to_track_quat('-Z','Y').to_euler()
def area(name,position,energy,size):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK'; data.size=size
    light=bpy.data.objects.new(name,data); scene.collection.objects.link(light); light.location=position; point(light,(0,0,3))
area('Key',(-6,-8,14),1600,8)
area('Fill',(8,-3,8),850,7)
area('Roof rim',(-1,8,13),1800,7)
camera_data=bpy.data.cameras.new('Presentation camera'); camera=bpy.data.objects.new('Presentation camera',camera_data)
scene.collection.objects.link(camera); scene.camera=camera
camera_data.type='ORTHO'; camera_data.ortho_scale=10.6
camera.location=(-10,-18,11); point(camera,(0,0,3.1))
scene.render.filepath=str(delivery/'医疗中心_模型预览.png')
bpy.ops.wm.save_as_mainfile(filepath=str(source_dir/'APDC_medical_center.blend'))
bpy.ops.render.render(write_still=True)
camera.location=(11,16,11); point(camera,(0,0,3.1))
scene.render.filepath=str(delivery/'医疗中心_背面预览.png'); bpy.ops.render.render(write_still=True)
camera.location=(-10,-18,11); point(camera,(0,0,3.1))
scene.render.resolution_x=256; scene.render.resolution_y=256
camera_data.ortho_scale=9.2
scene.cycles.samples=40
scene.render.filepath=str(source_dir/'APDC_medical_center_icon_render.png'); bpy.ops.render.render(write_still=True)
report={'model':str(mesh_path),'triangles':len(mesh.loop_triangles),'exported_vertices':exported_vertices,
        'materials':1,'texture_size':[1024,1024],'dimensions':list(obj.dimensions),
        'mesh_binary_roundtrip':True,'has_letters_or_logos':False,
        'front_preview':str(delivery/'医疗中心_模型预览.png'),'rear_preview':str(delivery/'医疗中心_背面预览.png')}
(source_dir/'model_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('APDC_MEDICAL_MODEL_COMPLETE '+json.dumps(report,ensure_ascii=False),flush=True)
