"""New chibi piggyback UMP sisters, modeled in 3D from the supplied pose reference."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_helpers import *
from gaits import foot_path,settings
import numpy as np,bmesh,xml.etree.ElementTree as ET
sys.path.append('D:/Desktop/第二批十套模型_待接入/制作脚本')
import geometry_core as G,batch_common as C
ident='APDC_ump_chibi';bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.fps=30
m=C.Model('ump_chibi');g=m.g
m.bones={'root':((0,0,0),None),'hull':((0,.05,1.55),'root'),'carrier_head':((0,-.88,1.83),'hull'),'carrier_hair':((0,-.62,2.15),'carrier_head'),'rider':((0,.17,2.30),'hull'),'rider_head':((0,-.03,3.46),'rider'),'rider_hair':((.58,.23,3.72),'rider_head'),'gun':((0,-.63,2.54),'rider'),'eyes':((0,-.697,3.56),'rider_head'),'mouth':((0,-.748,3.14),'rider_head')}
def ball(c,r,tile,bone,n=28,rows=16):C.ellipsoid(g,c,r,tile,bone,n,rows)
def tube(a,b,r,tile,bone,n=16):g.tube(a,b,r,tile,n,bone=bone)
def lock(points,width,depth,tile,bone):
 # Rounded, tapered clumps, unlike the old long triangular hair strips.
 control=[Vector(p) for p in points];pts=[]
 for i in range(len(control)-1):
  a,b,c,d=control[max(0,i-1)],control[i],control[i+1],control[min(len(control)-1,i+2)]
  for j in range(5):
   t=j/5;pts.append((2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)*.5)
 pts.append(control[-1]);rings=[]
 for j,p in enumerate(pts):
  tangent=(pts[min(j+1,len(pts)-1)]-pts[max(0,j-1)]).normalized();u=tangent.cross(Vector((0,-1,0)))
  if u.length<.1:u=Vector((1,0,0))
  u.normalize();v=tangent.cross(u).normalized();scale=(.90+.10*math.sin(math.pi*j/(len(pts)-1)))*(1-(j/(len(pts)-1))**5)
  if j==len(pts)-1:scale=.025
  rings.append([p+u*width*scale*math.cos(i*math.tau/10)+v*depth*scale*math.sin(i*math.tau/10) for i in range(10)])
 g.loft(rings,tile,bone)
def head(center,radius,hair,bone):
 x,y,z=center;rx,ry,rz=radius
 ball(center,radius,0,bone)
 # Hair shell only on rear/upper hemisphere; face stays unobstructed.
 for j in range(7):
  a=(j-3)*.35
  lock([(x+rx*math.sin(a)*.5,y-.04,z+rz*1.02),(x+rx*math.sin(a)*1.04,y-.44,z+rz*.78),(x+rx*math.sin(a)*1.08,y-ry*1.11,z+rz*.45),(x+rx*math.sin(a)*.95+.10,y-ry*1.12,z+rz*(.25+.08*math.sin(a*3)))],rx*.30,.043,hair,bone)
 for side in (-1,1):
  for j in range(4):
   yy=y+.04+j*.17
   lock([(x+side*rx*.67,yy,z+rz*.72),(x+side*rx*1.04,yy,z+rz*.23),(x+side*rx*1.09,yy,z-rz*.29),(x+side*rx*.89,yy-.07,z-rz*.54)],rx*.22,.12,hair,bone)
 ball((x,y+ry*.45,z+rz*.24),(rx*.90,ry*.74,rz*.83),hair,bone)
 for side in (-1,1):ball((x+side*rx*.75,y-ry*.79,z-rz*.21),(rx*.15,.024,rz*.075),7,bone,n=20,rows=10)
head((0,-.91,1.85),(.79,.65,.67),2,'carrier_head')
head((0,-.03,3.49),(.72,.61,.74),1,'rider_head')
# Carrier's >< eyes and joyful open mouth, matching the supplied exaggerated pose.
for side in (-1,1):
 x=side*.26;y=-1.546
 g.rail([(x+side*.12,y,1.94),(x-side*.07,y-.01,1.84),(x+side*.12,y,1.78)],.032,5,'carrier_head')
ball((0,-1.545,1.60),(.13,.027,.125),6,'carrier_head',24,12)
ball((0,-1.574,1.56),(.072,.014,.045),7,'carrier_head',20,10)
# Rider's amber anime eyes: dark outline, cream whites, amber iris, highlights.
for side in (-1,1):
 x=side*.27
 ball((x,-.610,3.56),(.194,.013,.243),5,'eyes')
 ball((x,-.621,3.57),(.174,.011,.220),8,'eyes')
 ball((x,-.632,3.54),(.143,.010,.184),9,'eyes')
 ball((x,-.642,3.53),(.069,.008,.126),10,'eyes')
 ball((x-.040,-.651,3.63),(.030,.005,.040),8,'eyes',16,8)
 g.rail([(x-.17,-.615,3.73),(x,-.634,3.81),(x+.16,-.612,3.74)],.016,5,'eyes')
ball((0,-.648,3.17),(.126,.035,.154),6,'mouth');ball((0,-.677,3.13),(.084,.014,.08),7,'mouth')
# Fringe, hair ties, and large swept ponytails; compact heads retain real depth.
for side in (-1,1):
 lock([(side*.22,-.18,4.14),(side*.38,-.57,3.99),(side*.48,-.64,3.74),(side*.56,-.56,3.49)],.20,.07,1,'rider_head')
 # Facing -Y: +X is her anatomical LEFT (viewer-right in a frontal view).
 # Top sister has only this single side ponytail; bottom sister keeps twins.
 if side==1:
  ball((side*.66,.16,3.85),(.10,.09,.19),4,'rider_head',18,10)
  lock([(side*.62,.18,3.85),(side*1.02,.51,3.88),(side*1.25,.66,3.55),(side*1.18,.82,3.09),(side*.92,1.01,2.93)],.36,.20,1,'rider_hair')
 lock([(side*.64,-.61,2.14),(side*1.0,-.31,2.01),(side*1.18,.03,1.78),(side*.98,.30,1.48)],.28,.18,2,'carrier_hair')
 ball((side*.64,-.61,2.17),(.105,.075,.13),4,'carrier_hair',16,10)
# Rounded black-and-yellow coats.
ball((0,.02,1.64),(.54,.76,.44),3,'hull')
ball((0,.12,2.57),(.43,.39,.49),3,'rider')
ball((0,.06,2.91),(.48,.42,.19),4,'rider')
ball((0,-.06,2.95),(.37,.29,.17),3,'rider')
C.panel(g,[(-.10,-.282,2.89),(.10,-.282,2.89),(.15,-.326,2.62),(0,-.35,2.71),(-.15,-.326,2.62)],.025,8,'rider')
g.rail([(0,-.38,2.73),(0,-.397,2.35),(0,-.32,2.16)],.028,4,'rider')
for side in (-1,1):
 # Articulated load-bearing arms: shoulders -> elbows -> palms on the ground.
 shoulder=(side*.50,-.36,1.34);elbow=(side*.74,-.24,.65);wrist=(side*.74,-.94,.19)
 upper,lower,hand=m.leg('carrier_front_'+str(side),shoulder,elbow,wrist,0.)
 C.beam(g,shoulder,elbow,.35,.36,3,upper,.86);ball(elbow,(.19,.19,.19),3,lower,20,10)
 C.beam(g,elbow,wrist,.31,.32,3,lower,.85)
 ball((side*.74,-.88,.32),(.20,.19,.14),4,lower)
 ball((side*.74,-1.04,.19),(.24,.30,.18),3,hand)
 for i in range(4):ball((side*.74+(i-1.5)*.066,-1.294,.105),(.040,.093,.075),0,hand,12,8)
 # Rider straddles, rather than being another upright figure beside her.
 C.beam(g,(side*.31,.18,2.23),(side*.69,-.01,1.99),.33,.34,3,'rider',.80)
 C.beam(g,(side*.69,-.01,1.99),(side*.70,.15,1.54),.26,.28,3,'rider',.85)
 ball((side*.71,.01,1.50),(.20,.32,.19),3,'rider');g.rail([(side*.56,-.16,1.56),(side*.84,-.16,1.56)],.045,4,'rider')
 C.beam(g,(side*.37,-.05,2.77),(side*.49,-.47,2.56),.30,.30,3,'gun',.80)
 C.beam(g,(side*.49,-.47,2.56),(side*.20,-.83,2.59),.28,.29,3,'gun',.82)
 g.rail([(side*.49-.13,-.43,2.60),(side*.49,-.46,2.72),(side*.49+.13,-.44,2.60)],.031,4,'gun')
 ball((side*.19,-.83,2.61),(.11,.13,.12),0,'gun',18,10)
 # Rear pair moves in unison, half a cycle behind the paired arms.
 hip=(side*.30,.60,1.30);knee=(side*.42,.08,.68);ankle=(side*.47,.88,.20)
 upper,lower,foot=m.leg('carrier_rear_'+str(side),hip,knee,ankle,.5)
 C.beam(g,hip,knee,.34,.35,3,upper,.87);ball(knee,(.18,.18,.18),3,lower,20,10)
 C.beam(g,knee,ankle,.28,.29,3,lower,.86)
 # Cover mechanical-looking joints with soft trousers and rounded boots.
 ball((side*.47,.79,.20),(.23,.36,.19),3,foot)
 g.rail([(side*.29,.54,.24),(side*.65,.54,.24)],.036,4,foot)
# Compact UMP SMG, not the discarded full-sized twin body arrangement.
g.box((0,-.86,2.69),(.19,.68,.24),5,'gun');g.box((0,-.90,2.832),(.12,.61,.035),10,'gun')
tube((0,-1.18,2.73),(0,-1.49,2.73),.045,5,'gun');tube((0,-1.46,2.73),(0,-1.56,2.73),.060,10,'gun')
g.box((0,-.71,2.40),(.12,.15,.42),5,'gun');g.box((0,-.52,2.47),(.115,.13,.23),5,'gun')
g.rail([(-.07,-.42,2.69),(-.09,-.08,2.67),(.09,-.08,2.67),(.07,-.42,2.69)],.032,5,'gun')
for x in (-.07,.07):tube((x,-1.14,2.80),(x,-1.14,2.91),.018,5,'gun',10)
g.rail([(-.07,-1.14,2.91),(0,-1.14,2.93),(.07,-1.14,2.91)],.013,5,'gun')
palette=[(.96,.80,.69),(.31,.23,.22),(.64,.39,.22),(.10,.105,.12),(.97,.70,.11),(.045,.040,.050),(.36,.09,.11),(.96,.40,.44),(.98,.96,.88),(.66,.38,.18),(.13,.13,.16),(.6,.6,.6),(.2,.2,.2),(.8,.8,.8),(.4,.4,.4),(.15,.15,.15)]
source=WORK/'source'/ident;source.mkdir(parents=True,exist_ok=True)
ims={}
for kind in ('diffuse','normal','specular'):
 arr=np.ones((256,256,4),np.float32)
 for i,col in enumerate(palette):arr[(i//4)*64:(i//4+1)*64,(i%4)*64:(i%4+1)*64]=(*col,1) if kind=='diffuse' else ((.5,.5,0,.5) if kind=='normal' else (0,.22,0,.23))
 im=bpy.data.images.new(ident+'_'+kind,width=256,height=256,alpha=True)
 # Palette is already display-referred. Save its numeric bytes as Non-Color,
 # then use sRGB on the resulting diffuse image for Blender preview.
 im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(arr.ravel());im.filepath_raw=str(source/(ident+'_'+kind+'.png'));im.file_format='PNG';im.save()
 if kind=='diffuse':im.colorspace_settings.name='sRGB'
 ims[kind]=im
rig=G.armature(m.bones);C.PREFIX='';ob=C.mesh(m,rig,[C.material(ident,ims)]);ob.name=ident;ob.data.name=ident+'Shape'
ob.data.set_sharp_from_angle(angle=math.radians(75));ob.data.update()
# Uniform palette tiles need continuous planar UVs, not a fresh full tile on
# every tiny sphere quad. This avoids 80k exported UV-split vertices while
# preserving the exact shape and maintaining non-degenerate tangent frames.
uv=ob.data.uv_layers.active
for poly in ob.data.polygons:
 olduv=uv.data[poly.loop_indices[0]].uv.copy();tx=int(olduv.x*4);ty=int(olduv.y*4)
 axis=max(range(3),key=lambda k:abs(poly.normal[k]));axes=[k for k in range(3) if k!=axis]
 for li in poly.loop_indices:
  p=ob.data.vertices[ob.data.loops[li].vertex_index].co
  uv.data[li].uv=((tx+.5+p[axes[0]]*.045)/4,(ty+.30+p[axes[1]]*.05)/4)
ob.data.update()
rig.name=ident+'_rig';clear_pose(rig);rig.data.pose_position='REST';select([ob,rig]);model=STAGE/'gfx/models/units'/ident;model.mkdir(parents=True,exist_ok=True)
io.export_meshfile(str(model/(ident+'.mesh')),exp_mesh=True,exp_skel=True,exp_locs=False,exp_selected=True)
tree=pdx.read_meshfile(str(model/(ident+'.mesh')))
for mat in tree.iter('material'):
 for key in ('diff','n','spec'):mat.set(key,[Path(mat.get(key)[0]).with_suffix('.dds').name])
for loc in list(tree.findall('locator')):tree.remove(loc)
locs=ET.SubElement(tree,'locator');loc=ET.SubElement(locs,'barrel');loc.set('p',[0.0,.19,-.93]);loc.set('q',[0.0,0.0,0.0,1.0]);loc.set('pa',['gun']);pdx.write_meshfile(str(model/(ident+'.mesh')),tree)
legs=m.legs
for leg in legs:
 h,k,a=[Vector(leg[key]) for key in ('hip','knee','ankle')];axis=(a-h).normalized()
 leg['pole']=(k-h-axis*(k-h).dot(axis)).normalized()
rig.data.pose_position='POSE';clips=['idle','idle_look','idle_shift','move','attack','death']
cfg=settings(ident);max_ik_error=0
bob_function=lambda t:-.035+.105*math.cos((t-.46)*math.tau*2)
crouch=reachable_body_offset(legs,cfg,bob_function)
for clip in clips:
 frames=91 if clip.startswith('idle') else (61 if clip=='death' else cfg['frames'] if clip=='move' else 31);begin(rig,ident+'_'+clip);prev={}
 for f in range(1,frames+1):
  scene.frame_set(f);clear_pose(rig);t=(f-1)/(frames-1);bob=crouch+bob_function(t) if clip=='move' else .026*math.sin(t*math.tau)
  rig.pose.bones['hull'].location.z=bob
  rig.pose.bones['rider'].rotation_quaternion=Euler((.025*math.sin(t*math.tau),.04*math.sin(t*math.tau),0)).to_quaternion()
  for n in ('carrier_hair','rider_hair'):rig.pose.bones[n].rotation_quaternion=Euler((.10*math.sin(t*math.tau),.12*math.sin(t*math.tau),.05*math.sin(t*math.tau))).to_quaternion()
  if clip=='move':
   rig.pose.bones['carrier_head'].rotation_quaternion=Euler((.085*math.sin(t*math.tau),0,0)).to_quaternion()
   rig.pose.bones['rider'].rotation_quaternion=Euler((.11*math.sin(t*math.tau+.5),0,0)).to_quaternion()
   for n in ('carrier_hair','rider_hair'):rig.pose.bones[n].rotation_quaternion=Euler((.17*math.sin(t*math.tau-.8),.035*math.sin(t*math.tau),0)).to_quaternion()
  if clip=='idle_look':
   rig.pose.bones['rider_head'].rotation_quaternion=Euler((.04*math.sin(t*math.tau),0,.28*math.sin(t*math.tau))).to_quaternion()
   rig.pose.bones['carrier_head'].rotation_quaternion=Euler((-.045*math.sin(t*math.tau),0,-.12*math.sin(t*math.tau))).to_quaternion()
  if clip=='idle_shift':
   rig.pose.bones['rider'].rotation_quaternion=Euler((.075*math.sin(t*math.tau),.07*math.sin(t*math.tau),0)).to_quaternion()
  blink=max(0,1-abs(t-.38)/.035);rig.pose.bones['eyes'].scale.z=1-.95*blink
  rig.pose.bones['mouth'].scale.z=1+.12*math.sin(t*math.tau)
  if clip=='attack':
   recoil=sum(max(0,1-abs(t-p)/.055) for p in (.18,.38,.58));rig.pose.bones['gun'].location.y=.085*recoil;rig.pose.bones['rider'].rotation_quaternion=Euler((.035*recoil,0,0)).to_quaternion()
  bpy.context.view_layer.update()
  for leg in legs:
   target=Vector(leg['ankle'])
   if clip=='move':
    dy,dz,_=foot_path(t,leg['phase'],cfg['stride'],cfg['lift'],cfg['duty']);target.y+=dy;target.z+=dz
   set_chain(rig,leg,target,bob)
   error=(rig.pose.bones[leg['bones'][2]].matrix.translation-target).length
   if error>max_ik_error:
    max_ik_error=error
    if error>.015:print('IK_TARGET_ERROR',clip,f,leg['bones'][0],error,flush=True)
  if clip=='death':
   q=min(1,t*1.7);rig.pose.bones['root'].rotation_quaternion=Euler((0,1.35*q,.2*q)).to_quaternion();rig.pose.bones['root'].location.z=.05*q
  for b in rig.pose.bones:
   if b.name in prev and b.rotation_quaternion.dot(prev[b.name])<0:b.rotation_quaternion.negate()
   prev[b.name]=b.rotation_quaternion.copy()
  key_all(rig,f)
 export_clip(rig,ident,clip,frames)
gfx,asset=ensure_asset(ident,clips,.92,'rifle_muzzle_particle');ent=STAGE/'gfx/entities';ent.mkdir(parents=True,exist_ok=True)
(ent/'APDC_ump_chibi.gfx').write_text('objectTypes = {\n'+gfx+'}\n','utf8');(ent/'APDC_ump_chibi.asset').write_text(asset,'utf8')
replace_definition('gfx/entities/zzz_APDC_unit_mapping.asset','apdc_ump_sisters_entity','entity = { clone = "APDC_ump_chibi_entity" name = "apdc_ump_sisters_entity" }')
rig.animation_data.action=bpy.data.actions[ident+'_idle'];scene.frame_set(1);save_source(ident,rig,[ob])
for clip,frame in [('idle',1),('move',9),('attack',13)]:rig.animation_data.action=bpy.data.actions[ident+'_'+clip];render(ident,rig,clip,frame)
assert max_ik_error<.015,('Unreachable hand/foot',max_ik_error)
save_json(WORK/'ump_validation.json',{'id':ident,'new_mesh':True,'reference':'89ddb1e40aa667a9794954adbdeddd7e.png','old_pair_mapping_replaced':True,'clips':clips,'bones':len(rig.data.bones),'vertices':len(ob.data.vertices),'triangles':len(ob.data.polygons),'smoking':False,'rider_ponytail':'anatomical_left_only','carrier_ponytails':2,'carrier_eyes':'><','gait':'paired_front_arms_then_paired_rear_legs','gait_settings':cfg,'maximum_ik_target_error':max_ik_error})
print('CHIBI_COMPLETE',flush=True)
