"""Convert generated building materials, append its UI frame, and validate files."""
from pathlib import Path
from PIL import Image
import hashlib
import io
import json
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
DELIVERY=Path(sys.argv[1])
SOURCE=ROOT/'art_source/medical_center'
MODEL=ROOT/'gfx/models/buildings/APDC_medical_center'
UI=ROOT/'gfx/interface/buildings'

def dds_mips(image,path):
    # Standard legacy DXT5 header + a complete BC3 mip chain (no DX10 extension).
    buffers=[]; base_header=None; level=image.convert('RGBA')
    while True:
        buffer=io.BytesIO(); level.save(buffer,format='DDS',pixel_format='DXT5')
        data=buffer.getvalue()
        assert data[:4]==b'DDS ' and data[84:88]==b'DXT5'
        if base_header is None:
            base_header=bytearray(data[:128])
        buffers.append(data[128:])
        if level.size==(1,1):
            break
        level=level.resize((max(1,level.width//2),max(1,level.height//2)),Image.Resampling.LANCZOS)
    flags=struct.unpack_from('<I',base_header,8)[0] | 0x20000
    struct.pack_into('<I',base_header,8,flags)
    struct.pack_into('<I',base_header,28,len(buffers))
    struct.pack_into('<I',base_header,108,0x401008)
    path.write_bytes(bytes(base_header)+b''.join(buffers))
    with Image.open(path) as check:
        assert check.size==image.size
        check.load()
    return {'path':str(path.relative_to(ROOT)), 'mip_levels':len(buffers),
            'bytes':path.stat().st_size,'format':'DXT5/BC3','size':list(image.size),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

materials=[]
for kind in ('diffuse','normal','specular'):
    path=SOURCE/f'APDC_medical_center_{kind}.png'
    with Image.open(path) as image:
        materials.append(dds_mips(image,MODEL/f'APDC_medical_center_{kind}.dds'))

original=ROOT/'gfx/interface/buildings/building_icon_strip.dds'
if not original.exists():
    original=GAME/'gfx/interface/buildings/building_icon_strip.dds'
with Image.open(original) as image:
    original_strip=image.convert('RGBA')
assert original_strip.size==(46*31,46)
with Image.open(SOURCE/'APDC_medical_center_icon_render.png') as image:
    render=image.convert('RGBA')
crop=render.crop(render.getbbox())
icon=Image.new('RGBA',(46,46),(0,0,0,0))
crop.thumbnail((42,43),Image.Resampling.LANCZOS)
icon.alpha_composite(crop,((46-crop.width)//2,(46-crop.height)//2))
icon.save(UI/'APDC_medical_center_icon.dds',format='DDS')
strip=Image.new('RGBA',(46*32,46),(0,0,0,0))
strip.paste(original_strip,(0,0)); strip.paste(icon,(46*31,0))
strip.save(UI/'APDC_building_icon_strip.dds',format='DDS')
with Image.open(UI/'APDC_building_icon_strip.dds') as image:
    assert image.convert('RGBA').crop((0,0,46*31,46)).tobytes()==original_strip.tobytes()
    assert image.convert('RGBA').crop((46*31,0,46*32,46)).tobytes()==icon.tobytes()
icon.save(DELIVERY/'医疗中心_建造图标.png')

# Copy the editable, self-contained Blender source and game asset bundle for delivery.
shutil.copy2(SOURCE/'APDC_medical_center.blend',DELIVERY/'医疗中心.blend')
exported=DELIVERY/'钢四模型文件'
exported.mkdir(exist_ok=True)
for path in MODEL.iterdir():
    if path.suffix in ('.mesh','.dds'):
        shutil.copy2(path,exported/path.name)
validation=json.loads((SOURCE/'model_validation.json').read_text(encoding='utf-8'))
validation.update({'materials':materials,'icon_frames':32,'original_icon_frames_preserved':31,
                   'startup_unlock':True,'bonuses':None,'construction_cost':6000,'max_per_state':1,
                   'game_runtime_tested':False})
(SOURCE/'model_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2(SOURCE/'model_validation.json',DELIVERY/'文件验证记录.json')
print(json.dumps(validation,ensure_ascii=False))
