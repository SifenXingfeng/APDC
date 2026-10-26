"""Build a sunglasses-wearing movie-inspired penguin on an adapted HOI4 rig.

Background Blender 4.2; no game/UI control. Vanilla assets are read-only inputs.
"""
import argparse
import copy
import importlib
import json
import logging
import math
from pathlib import Path
import sys
import types
import bpy
import bmesh
import numpy as np
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--project', required=True)
parser.add_argument('--exporter', required=True)
parser.add_argument('--delivery', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
ROOT = Path(args.project)
SOURCE = ROOT/'art_source/penguin_infantry'
MODEL = ROOT/'gfx/models/units/APDC_penguin'
DELIVERY = Path(args.delivery)
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
UNITS = GAME/'gfx/models/units'
for directory in [SOURCE, MODEL, DELIVERY]:
    directory.mkdir(parents=True, exist_ok=True)
pkg = types.ModuleType('io_pdx_mesh'); pkg.__path__ = [args.exporter]
pkg.IO_PDX_LOG = logging.getLogger('io_pdx'); sys.modules[pkg.__name__] = pkg
sub = types.ModuleType('io_pdx_mesh.pdx_blender')
sub.__path__ = [str(Path(args.exporter)/'pdx_blender')]; sys.modules[sub.__name__] = sub
backend = importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
pdx = importlib.import_module('io_pdx_mesh.pdx_data')
backend.create_material = lambda *a: None
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
backend.import_meshfile(str(UNITS/'GER_infantry.mesh'), imp_mesh=False, imp_skel=True, imp_locs=True)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.name = 'APDC_penguin_original_infantry_rig'
rig.data.pose_position = 'REST'
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from retarget import adapt
adaptation=adapt(rig,backend,pdx,MODEL,UNITS,ROOT/'gfx/entities/APDC_penguin_infantry.gfx')

def smooth(a,b,x):
    t = min(1.0,max(0.0,(x-a)/(b-a)))
    return t*t*(3-2*t)

# Atlas: left 75% seamless body; right 25% accessory surfaces, eight swatches.
SIZE = 1024
rng = np.random.default_rng(20260909)
yy, xx = np.mgrid[0:SIZE,0:SIZE]
u = xx/(SIZE-1); v = yy/(SIZE-1)
phi = (u/.75-.5)*math.tau
black = np.array([.048,.060,.075]); white = np.array([.91,.935,.915])
boundary = 1.08 + .14*np.exp(-((v-.38)/.25)**2) - .08*np.exp(-((v-.72)/.13)**2)
cap = .915 + .036*np.exp(-((np.abs(phi)-.47)/.31)**2) - .10*np.maximum(np.abs(phi)-.78,0)
mask = (np.abs(phi)<boundary)&(v<cap)
diff = np.ones((SIZE,SIZE,4),dtype=np.float32)
noise = rng.normal(0,.003,(SIZE,SIZE)) + .0018*np.sin(xx*.93+np.sin(yy*.2))
shade = 1-.045*np.exp(-((v-.03)/.12)**2)
diff[:,:,:3] = np.where(mask[:,:,None],white,black)*shade[:,:,None]+noise[:,:,None]
normal = np.ones_like(diff); normal[:] = (.5,.5,0,.5)
spec = np.ones_like(diff); spec[:] = (0,.34,0,.28)
# black feather, orange bill, lower bill, feet, frame, lens, mouth, highlight.
colours = [(.048,.060,.075),(.96,.46,.055),(.72,.24,.025),(.94,.39,.045),
           (.62,.66,.68),(.018,.035,.055),(.035,.018,.014),(.26,.36,.42)]
for i, colour in enumerate(colours):
    row = slice(i*128,(i+1)*128); column=slice(768,1024)
    sx=(xx[row,column]-768)/255; sy=(yy[row,column]-i*128)/127
    tile=np.broadcast_to(np.array(colour),(128,256,3)).copy()
    tile += rng.normal(0,.002,(128,256,1))
    if i==5:
        tile += (.07*np.exp(-((sy-.70-.20*sx)/.10)**2))[:,:,None]*np.array([.6,.8,1])
    if i in (1,2,3):
        tile *= (0.94+.08*sy[:,:,None])
    diff[row,column,:3]=tile
    spec[row,column]=(0,.75 if i in (4,5) else .4,.8 if i==4 else 0,.86 if i in (4,5) else .36)
diff[:,:,:3]=np.clip(diff[:,:,:3],0,1)

def image_from_array(name, values, data=False):
    image=bpy.data.images.new(name,SIZE,SIZE,alpha=True)
    if data: image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set(values.ravel())
    image.filepath_raw=str(SOURCE/(name+'.png')); image.file_format='PNG'; image.save()
    return image

images={kind:image_from_array('APDC_penguin_'+kind,arr,kind!='diffuse')
        for kind,arr in [('diffuse',diff),('normal',normal),('specular',spec)]}
mat=bpy.data.materials.new('APDC_penguin_material'); mat.use_nodes=True; mat['shader']='PdxMeshAdvanced'
n,l=mat.node_tree.nodes,mat.node_tree.links
bs=n.get('Principled BSDF')
color=n.new('ShaderNodeTexImage');color.image=images['diffuse'];l.new(color.outputs['Color'],bs.inputs['Base Color'])
prop=n.new('ShaderNodeTexImage');prop.image=images['specular']
split=n.new('ShaderNodeSeparateColor');l.new(prop.outputs['Color'],split.inputs[0])
l.new(split.outputs['Green'],bs.inputs['Specular IOR Level']);l.new(split.outputs['Blue'],bs.inputs['Metallic'])
inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
l.new(prop.outputs['Alpha'],inv.inputs[1]);l.new(inv.outputs[0],bs.inputs['Roughness'])
nt=n.new('ShaderNodeTexImage');nt.image=images['normal']
ns=n.new('ShaderNodeSeparateColor');l.new(nt.outputs[0],ns.inputs[0])
nc=n.new('ShaderNodeCombineColor');nc.inputs[2].default_value=1
l.new(ns.outputs['Green'],nc.inputs[0]);l.new(nt.outputs['Alpha'],nc.inputs[1])
nm=n.new('ShaderNodeNormalMap');l.new(nc.outputs[0],nm.inputs[0]);l.new(nm.outputs[0],bs.inputs['Normal'])

class Geometry:
    def __init__(self): self.v=[];self.f=[];self.uv=[];self.weights=[];self.parts={}
    def vert(self,p,uv,w):
        self.v.append(tuple(p));self.uv.append(uv)
        w={k:float(value) for k,value in w.items() if value>1e-7}; total=sum(w.values())
        assert total>0 and len(w)<=4
        self.weights.append({k:v/total for k,v in w.items()});return len(self.v)-1
    def face(self,*indices):self.f.append(tuple(indices))
    def swatch(self,slot,u=.5,v=.5):return (.765+u*.22,(slot+.08+v*.84)/8)
    def surface(self,name,nu,nv,position,weight,slot=None,reverse=False):
        start=len(self.v)
        for j in range(nv+1):
            for i in range(nu+1):
                u,v=i/nu,j/nv;p=position(u,v)
                uv=(u*.745+.002,v*.996+.002) if slot is None else self.swatch(slot,u,v)
                self.vert(p,uv,weight(p,u,v))
        for j in range(nv):
            for i in range(nu):
                a=start+j*(nu+1)+i; q=(a,a+1,a+nu+2,a+nu+1)
                self.face(*(reversed(q) if reverse else q))
        self.parts[name]=[start,len(self.v)]
    def ellipsoid(self,name,center,radii,weights,slot,nu=28,nv=14):
        c=Vector(center)
        def pos(u,v):
            ph=u*math.tau;th=(.0001+v*.9998)*math.pi
            return c+Vector((radii[0]*math.sin(th)*math.cos(ph),radii[1]*math.sin(th)*math.sin(ph),radii[2]*math.cos(th)))
        self.surface(name,nu,nv,pos,lambda *a:weights,slot,True)
    def tube(self,name,points,radius,weights,slot,sides=8):
        start=len(self.v)
        for j,p in enumerate(points):
            p=Vector(p)
            tangent=Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])
            tangent.normalize();ref=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            x=tangent.cross(ref).normalized();y=tangent.cross(x).normalized()
            for i in range(sides+1):
                ph=i/sides*math.tau
                self.vert(p+radius*(x*math.cos(ph)+y*math.sin(ph)),self.swatch(slot,i/sides,j/(len(points)-1)),weights)
        for j in range(len(points)-1):
            for i in range(sides):
                a=start+j*(sides+1)+i;self.face(a,a+1,a+sides+2,a+sides+1)
        self.parts[name]=[start,len(self.v)]

g=Geometry()
# Catmull-Rom rounded silhouette: squat abdomen, sloping shoulders, low domed crown.
profile=[(.72,.04,.04,.10),(1.00,.88,.72,.06),(1.52,1.54,1.08,.06),
         (2.35,1.84,1.23,.06),(3.15,1.79,1.23,.02),(4.20,1.56,1.06,.01),
         (5.25,1.30,.88,.03),(6.12,1.23,.86,.05),(6.78,1.11,.80,.07),
         (7.12,.85,.65,.09),(7.35,.36,.33,.10),(7.40,.015,.015,.10)]

def shape_at(z):
    for j in range(len(profile)-1):
        if profile[j][0]<=z<=profile[j+1][0]:break
    t=(z-profile[j][0])/(profile[j+1][0]-profile[j][0])
    p0=np.array(profile[max(j-1,0)][1:]);p1=np.array(profile[j][1:])
    p2=np.array(profile[j+1][1:]);p3=np.array(profile[min(j+2,len(profile)-1)][1:])
    return .5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)

def body_pos(u,v):
    z=.72+6.68*v;rx,ry,cy=shape_at(z);ph=(u-.5)*math.tau
    return (rx*math.sin(ph),cy-ry*math.cos(ph),z)
def body_weights(p,u,v):
    x,y,z=p;h=smooth(5.15,6.55,z);back=smooth(1.75,5.25,z)*(1-h)
    w={'Hip':1-h-back,'back_mid':back,'head':h}
    # Keep the continuous feather skirt on the torso, avoiding knee-driven dents.
    return w
g.surface('body',48,40,body_pos,body_weights)

# Broad curved upper/lower beak, with a real narrow mouth seam, not a texture decal.
def beak_surface(u,v,upper=True):
    x=(u*2-1)*1.055;a=abs(x/1.055)
    back=-.59-.18*(1-a*a);front=-.72-1.08*(max(0,math.cos(a*math.pi/2))**.64)
    y=back*(1-v)+front*v;seam=6.09+.13*a
    rise=(.33 if upper else -.21)*(1-a*a)*math.sin(v*math.pi)
    z=seam+rise+(.012 if upper else -.012)
    return (x,y,z)
g.surface('upper_beak',28,10,lambda u,v:beak_surface(u,v,True),lambda *a:{'head':1},1,True)
g.surface('lower_beak',28,10,lambda u,v:beak_surface(u,v,False),lambda *a:{'head':1},2)
line=[]
for i in range(41):
    p=Vector(beak_surface(i/40,1,True));p.z=6.09+.13*abs(p.x/1.055);line.append(p)
g.tube('mouth_seam',line,.018,{'head':1},6,6)

# Aviator-style silver rim, dark reflective lenses, bridge and wraparound temples.
def lens_point(side,angle,scale=1):
    x=side*(.59+.52*math.cos(angle)*scale)
    z=6.68+.39*math.sin(angle)*scale-.045*max(0,-math.sin(angle))
    y=-.985+.26*(abs(x)/1.18)**2
    return Vector((x,y,z))
for side in (-1,1):
    ring=[lens_point(side,i/36*math.tau) for i in range(37)]
    g.tube('glasses_rim_'+str(side),ring,.048,{'head':1},4,6)
    def lenspos(u,v,side=side):
        # Radial patch; convex front bulge, slightly behind the rim edge.
        p=lens_point(side,u*math.tau,v*.945)
        p.y-=.055*(1-v*v);return p
    g.surface('lens_'+str(side),36,6,lenspos,lambda *a:{'head':1},5,side<0)
    points=[(side*.12,-1.015,6.82),(side*.045,-1.06,6.855),(-side*.04,-1.06,6.855)]
    if side==1:g.tube('bridge',points,.045,{'head':1},4,8)
    points=[(side*1.11,-.75,6.86),(side*1.18,-.52,6.88),(side*1.20,-.12,6.83),(side*1.16,.34,6.72),(side*1.09,.52,6.54)]
    g.tube('temple_'+str(side),points,.065,{'head':1},0,8)

# Flippers follow original upper-arm/elbow/forearm/hand joints; no humanoid fingers.
for side,label in [(1,'Left'),(-1,'Right')]:
    names=[label+'Arm',label+'ForeArm',label+'ForeArmRoll',label+'Hand']
    points=[rig.data.bones[name].head_local.copy() for name in names]
    points.append(points[-1]+Vector((side*.37,-.19,-.47)))
    fractions=[0,.40,.61,.80,1]
    def fin_data(v):
        j=next((j for j in range(4) if fractions[j]<=v<=fractions[j+1]),3)
        t=(v-fractions[j])/(fractions[j+1]-fractions[j]);p=points[j].lerp(points[j+1],t)
        tangent=(points[j+1]-points[j]).normalized()
        width=np.interp(v,[0,.16,.48,.76,.95,1],[.26,.39,.42,.29,.10,.025])
        thickness=np.interp(v,[0,.4,.8,1],[.13,.13,.085,.025])
        w={names[min(j,3)]:1-t}
        second=names[min(j+1,3)];w[second]=w.get(second,0)+t
        return p,tangent,width,thickness,w
    def finpos(u,v):
        p,tangent,width,thickness,w=fin_data(v)
        perpendicular=Vector((-tangent.z,0,tangent.x)).normalized()
        ph=u*math.tau
        return p+perpendicular*width*math.cos(ph)+Vector((0,thickness*math.sin(ph),0))
    g.surface(label+'_flipper',12,24,finpos,lambda p,u,v:fin_data(v)[4],0,side<0)
    # Hidden slim feather shank joins the ankle into the underside of the body.
    ankle=rig.data.bones[label+'Foot'].head_local.copy()
    g.ellipsoid(label+'_ankle',ankle+Vector((0,0,.23)),(.22,.25,.43),{label+'Foot':.75,label+'Leg':.25},3,14,8)
    center=(side*.92,-.10,.20)
    g.ellipsoid(label+'_foot_web',center,(.63,.63,.19),{label+'Foot':1},3,18,8)
    for toe in (-1,0,1):
        g.ellipsoid(label+'_toe_'+str(toe),(side*.92+toe*.36,-.60+abs(toe)*.12,.15),(.235,.42,.145),{label+'Foot':.65,label+'ToeBase':.35},3,14,8)

# Small black tail, hidden by the body from the front, follows the pelvis.
g.ellipsoid('tail',(0,1.13,1.58),(.48,.66,.29),{'Hip':1},0,16,8)
mesh=bpy.data.meshes.new('APDC_penguinShape');mesh.from_pydata(g.v,[],g.f);mesh.update()
body=bpy.data.objects.new('APDC_penguin',mesh);bpy.context.collection.objects.link(body)
mesh.materials.append(mat)
uv=mesh.uv_layers.new(name='UVMap')
for p in mesh.polygons:
    p.use_smooth=True
    for li in p.loop_indices:uv.data[li].uv=g.uv[mesh.loops[li].vertex_index]
for bone in rig.data.bones:body.vertex_groups.new(name=bone.name)
for i,w in enumerate(g.weights):
    for name,value in w.items():body.vertex_groups[name].add([i],value,'REPLACE')
mod=body.modifiers.new('Original_infantry_skin','ARMATURE');mod.object=rig
body.parent=rig
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
backend.export_meshfile(str(MODEL/'APDC_penguin.mesh'),exp_mesh=True,exp_skel=True,exp_locs=True)
# Texture references must target the DDS files shipped to the engine, not PNG sources.
tree=pdx.read_meshfile(str(MODEL/'APDC_penguin.mesh'))
for material in tree.iter('material'):
    for field in ('diff','n','spec'):
        material.set(field,[str(Path(material.get(field)[0]).with_suffix('.dds'))])
exported=tree.find('object/APDC_penguinShape/mesh')
exported_skel=tree.find('object/APDC_penguinShape/skeleton')
original=pdx.read_meshfile(str(UNITS/'GER_infantry.mesh')).find('object/GER_infantryShape/skeleton')
assert [b.tag for b in exported_skel]==[b.tag for b in original]
weighted_names={name for weights in g.weights for name in weights}
changed_joints=set(adaptation['joint_world_deltas_game'])
weighted_bind_error=max(abs(x-y) for a,b in zip(exported_skel,original) if a.tag in weighted_names-changed_joints for x,y in zip(a.get('tx'),b.get('tx')))
assert weighted_bind_error<.001,weighted_bind_error
# The importer deliberately normalises nearly-zero-scale attachment bones.
# Preserve the original inverse-bind rotations/scales and apply only the explicit
# penguin joint translations. Bone names, order and parents remain identical.
for exported_bone,original_bone in zip(exported_skel,original):
    exported_bone.attrib=copy.deepcopy(original_bone.attrib)
    if exported_bone.tag in changed_joints:
        delta=adaptation['joint_world_deltas_game'][exported_bone.tag]
        tx=list(original_bone.get('tx'))
        # Translate the original inverse bind matrix analytically, retaining
        # tiny-scale attachment data that a DCC importer normally normalises.
        for row in range(3):tx[9+row]-=sum(tx[row+3*col]*delta[col] for col in range(3))
        exported_bone.set('tx',tx)
max_bind_error=weighted_bind_error
pdx.write_meshfile(str(MODEL/'APDC_penguin.mesh'),tree)
weights=exported.find('skin').get('w');assert all(abs(sum(weights[i:i+4])-1)<1e-5 for i in range(0,len(weights),4))
record={'triangles':len(exported.get('tri'))//3,'exported_vertices':len(exported.get('p'))//3,
        'bones':len(exported_skel),'max_influences':4,'unchanged_joint_export_error_before_exact_restore':max_bind_error,
        'rig':'vanilla 33-joint topology, shortened penguin legs and adapted animation copies','game_runtime_tested':False,
        'rig_adaptation':adaptation,'rest_dimensions':list(body.dimensions),'entity_scale':.77,'parts':g.parts}
(SOURCE/'validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')

# Lighting and reference camera. Original weapon is a preview-only runtime attachment.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
scene.world.color=(.25,.25,.25)
scene.view_settings.view_transform='AgX'
def aim(obj,p):obj.rotation_euler=(Vector(p)-obj.location).to_track_quat('-Z','Y').to_euler()
def light(name,loc,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=loc;aim(obj,(0,0,3.8))
light('Key',(-6,-10,13),1700,7);light('Fill',(7,-5,8),1000,6);light('Rim',(2,7,11),2000,5)
camera=bpy.data.objects.new('Penguin_preview_camera',bpy.data.cameras.new('Penguin_preview_camera'))
bpy.context.collection.objects.link(camera);camera.data.type='ORTHO';camera.data.ortho_scale=10.3
camera.location=(10,-17,10);aim(camera,(0,0,3.6));scene.camera=camera
rig.data.pose_position='POSE'
backend.import_animfile(str(MODEL/'animations/APDC_GER_infantry_idle_rifle.anim'));scene.frame_set(1)
for image in images.values():image.pack()
bpy.context.view_layer.objects.active=body;body.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'APDC_penguin.blend'))
scene.render.filepath=str(DELIVERY/'企鹅步兵_待机模型初稿.png');bpy.ops.render.render(write_still=True)
print('PENGUIN_MODEL_EXPORTED '+json.dumps({k:v for k,v in record.items() if k not in ('parts','rig_adaptation')}),flush=True)
