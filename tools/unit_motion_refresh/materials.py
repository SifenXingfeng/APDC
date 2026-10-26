"""Repair the extra sRGB decoding in generated vehicle albedo; keep data maps unchanged."""
from common import *
from PIL import Image
import numpy as np,io,struct
def dds(image,path):
 chunks=[];head=None;level=image.convert('RGBA')
 while True:
  buf=io.BytesIO();level.save(buf,format='DDS',pixel_format='DXT5');data=buf.getvalue()
  if head is None:head=bytearray(data[:128])
  chunks.append(data[128:])
  if level.size==(1,1):break
  level=level.resize((max(1,level.width//2),max(1,level.height//2)),Image.Resampling.LANCZOS)
 struct.pack_into('<I',head,8,struct.unpack_from('<I',head,8)[0]|0x20000);struct.pack_into('<I',head,28,len(chunks));struct.pack_into('<I',head,108,0x401008)
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(bytes(head)+b''.join(chunks))
records=[]
for ident,entry in sources().items():
 info=entry['info'];kind=info.get('kind','')
 if not (ident.startswith('APDC_v5_') or kind in ('tracked','wheeled','truck','helicopter')):continue
 src=Path(entry['blend']).parent;model=ROOT/'gfx/models/units'/ident
 for target in model.glob('*diffuse.dds'):
  png=src/(target.stem+'.png')
  if not png.exists():raise FileNotFoundError(png)
  old=np.array(Image.open(png).convert('RGBA'));linear=old[:,:,:3].astype(np.float32)/255
  encoded=np.where(linear<=.0031308,linear*12.92,1.055*np.power(linear,1/2.4)-.055)
  fixed=old.copy();fixed[:,:,:3]=np.clip(np.rint(encoded*255),0,255).astype(np.uint8)
  out=STAGE/target.relative_to(ROOT);dds(Image.fromarray(fixed),out)
  records.append({'file':str(target.relative_to(ROOT)),'source':str(png),'before_sha256':sha(target),'mean_rgb_before':old[:,:,:3].mean(axis=(0,1)).tolist(),'mean_rgb_after':fixed[:,:,:3].mean(axis=(0,1)).tolist(),'alpha_unchanged':bool(np.array_equal(old[:,:,3],fixed[:,:,3]))})
save_json(WORK/'material_validation.json',{'correction':'inverse of erroneous prior sRGB decode, not an arbitrary brightness multiplier','shader_source':str(GAME/'gfx/FX/standardfuncsgfx.fxh'),'data_textures_unchanged':True,'files':records})
print('VEHICLE_ALBEDO_REPAIRED',len(records),flush=True)
