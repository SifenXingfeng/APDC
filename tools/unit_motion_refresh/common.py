from pathlib import Path
import sys, types, importlib, logging, json, hashlib
ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'art_source/unit_motion_refresh'
STAGE=WORK/'staging'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
ADDON=Path('C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh')
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,patches
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=[str(ADDON)];pkg.IO_PDX_LOG=logging.getLogger('pdx');sys.modules[pkg.__name__]=pkg
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
def backend():
 sub=types.ModuleType('io_pdx_mesh.pdx_blender');sub.__path__=[str(ADDON/'pdx_blender')];sys.modules[sub.__name__]=sub
 return importlib.import_module('io_pdx_mesh.pdx_blender.blender_import_export')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf8')
def sources():
 result={}
 for pack in ('第二批十套模型_待接入','剩余六套单位与步枪_待接入','模型收尾_涅托与武器变体','通用车辆五套模型_待接入'):
  for path in (Path('D:/Desktop')/pack/'可编辑源文件').glob('*/model_info.json'):
   info=json.loads(path.read_text('utf-8-sig'));blend=next(path.parent.glob('*.blend'))
   result[blend.stem]={'info':info,'blend':str(blend),'label':path.parent.name}
 return result
if __name__=='__main__':
 from PIL import Image
 import numpy as np
 result={}
 for path in (ROOT/'gfx/models/units').glob('APDC_*/*.mesh'):
  tree=pdx.read_meshfile(str(path));record={'objects':[],'locators':[]}
  for obj in tree.find('object'):
   record['objects'].append({'name':obj.tag,'bones':[b.tag for b in obj.find('skeleton')] if obj.find('skeleton') is not None else [],'materials':[m.find('material').attrib for m in obj.findall('mesh')]})
  locs=tree.find('locator');record['locators']=[(l.tag,l.attrib) for l in locs] if locs is not None else []
  result[path.stem]=record
 save_json(WORK/'inventory.json',{'models':result,'sources':sources()})
 for key,r in result.items():
  if key.startswith(('APDC_r6','APDC_b2','APDC_f1_nyto')):print(key,[o['bones'] for o in r['objects']],r['locators'])
 for path in [ROOT/'gfx/models/units/APDC_v5_mbt/APDC_v5_mbt_diffuse.dds',ROOT/'gfx/models/units/APDC_v5_mbt/APDC_v5_mbt_normal.dds',GAME/'gfx/models/units/GER_medium_tank_1_diffuse.dds']:
  if path.exists():
   im=np.asarray(Image.open(path).convert('RGBA'));print(path.name,im.shape,im.mean(axis=(0,1)),np.percentile(im[:,:,:3],[10,50,90]))
