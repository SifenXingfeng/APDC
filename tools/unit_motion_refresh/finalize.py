from common import *
import io,struct,shutil
from PIL import Image
def dds(image,path):
 chunks=[];head=None;level=image.convert('RGBA')
 while True:
  buf=io.BytesIO();level.save(buf,format='DDS',pixel_format='DXT5');data=buf.getvalue()
  if head is None:head=bytearray(data[:128])
  chunks.append(data[128:])
  if level.size==(1,1):break
  level=level.resize((max(1,level.width//2),max(1,level.height//2)),Image.Resampling.LANCZOS)
 struct.pack_into('<I',head,8,struct.unpack_from('<I',head,8)[0]|0x20000);struct.pack_into('<I',head,28,len(chunks));struct.pack_into('<I',head,108,0x401008)
 path.write_bytes(bytes(head)+b''.join(chunks))
for path in (WORK/'source/APDC_ump_chibi').glob('*.png'):
 dds(Image.open(path),STAGE/'gfx/models/units/APDC_ump_chibi'/(path.stem+'.dds'))
# Generic infantry gets the same smoke-free policy; do not alter non-smoking states.
rel=Path('gfx/entities/APDC_r6_models.asset');out=STAGE/rel;text=out.read_text('utf8');node=next(n for n in parse(text) if n.val('name')=='APDC_r6_infantry_entity');edits=[]
for n in node.children:
 if n.key=='state' and n.val('animation')=='long_idle03':edits.append((n.start,n.end,''))
 if n.key=='attach' and any(s in n.val('name','') for s in ('cigarette','lighter')):edits.append((n.start,n.end,''))
out.write_text(patches(text,edits),'utf8')
# Stop unused legacy UMP definitions from being selectable accidentally. Files
# remain recoverable in the prior pack; only the active entity/mesh registrations
# are retired, while all unit aliases now resolve to the new combined model.
for suffix in ('asset','gfx'):
 out=STAGE/('gfx/entities/APDC_r6_models.'+suffix);text=out.read_text('utf8');nodes=parse(text);nodes=nodes[0].children if suffix=='gfx' else nodes
 edits=[(n.start,n.end,'') for n in nodes if n.val('name','').startswith(('APDC_r6_ump45_','APDC_r6_ump9_'))]
 out.write_text(patches(text,edits),'utf8')
save_json(WORK/'scope.json',{'humanoid_vanilla':['APDC_r6_tactical_doll'],'seated_upper_vanilla':['APDC_r6_lyuba'],'new_chibi':['APDC_ump_chibi'],'existing_motion_models':[x['id'] for x in json.loads((WORK/'motion_validation.json').read_text('utf8'))],'retired_active_entities':['APDC_r6_ump45_entity','APDC_r6_ump9_entity'],'vehicle_albedo_files':len(json.loads((WORK/'material_validation.json').read_text('utf8'))['files']),'unit_parameters_changed':False,'original_game_files_changed':False})
print('FINALIZED',len(list(STAGE.rglob('*'))),flush=True)
