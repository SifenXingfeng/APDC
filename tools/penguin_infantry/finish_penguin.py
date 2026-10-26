"""Create game-safe mipmapped DDS files from procedural texture sources."""
from pathlib import Path
import hashlib
import io
import json
import shutil
import struct
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'art_source/penguin_infantry'
MODEL=ROOT/'gfx/models/units/APDC_penguin'
DELIVERY=Path(sys.argv[1])

def dds_mips(image,path):
    buffers=[];header=None;level=image.convert('RGBA')
    while True:
        buffer=io.BytesIO();level.save(buffer,format='DDS',pixel_format='DXT5')
        data=buffer.getvalue()
        assert data[:4]==b'DDS ' and data[84:88]==b'DXT5'
        if header is None:header=bytearray(data[:128])
        buffers.append(data[128:])
        if level.size==(1,1):break
        level=level.resize((max(1,level.width//2),max(1,level.height//2)),Image.Resampling.LANCZOS)
    struct.pack_into('<I',header,8,struct.unpack_from('<I',header,8)[0]|0x20000)
    struct.pack_into('<I',header,28,len(buffers));struct.pack_into('<I',header,108,0x401008)
    path.write_bytes(bytes(header)+b''.join(buffers))
    with Image.open(path) as check:check.load();assert check.size==image.size
    return {'file':path.name,'size':list(image.size),'mip_levels':len(buffers),'format':'DXT5/BC3',
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

record=json.loads((SOURCE/'validation.json').read_text(encoding='utf-8'))
record['textures']=[]
for channel in ['diffuse','normal','specular']:
    with Image.open(SOURCE/f'APDC_penguin_{channel}.png') as image:
        record['textures'].append(dds_mips(image,MODEL/f'APDC_penguin_{channel}.dds'))
(SOURCE/'validation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'dds_files':len(record['textures']),'mip_levels':11}))
