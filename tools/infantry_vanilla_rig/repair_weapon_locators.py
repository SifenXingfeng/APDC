"""One-off correction of exporter placeholder locator containers; body unchanged."""
from pathlib import Path
import sys,types,importlib,copy
ROOT=Path(__file__).resolve().parents[2]
pkg=types.ModuleType('io_pdx_mesh');pkg.__path__=['C:/Users/ASUS/AppData/Local/Temp/apdc_medical_tools_20260909/io_pdx_mesh'];sys.modules[pkg.__name__]=pkg
pdx=importlib.import_module('io_pdx_mesh.pdx_data')
path=ROOT/'art_source/infantry_vanilla_rig/staging/gfx/models/units/APDC_vanilla_infantry/APDC_AK12_attachment.mesh'
tree=pdx.read_meshfile(str(path));containers=tree.findall('locator')
original=pdx.read_meshfile('D:/SteamLibrary/steamapps/common/Hearts of Iron IV/gfx/models/units/GER_infantry_weapon_k98_rifle.mesh')
good=copy.deepcopy(original.find('locator'))
for c in containers:tree.remove(c)
for loc in good:
 loc.set('p',[0.0,.16*1.9+.06,-1.34*1.9-.20] if loc.tag=='muzzle' else [.16*1.9,.177*1.9+.06,.19*1.9-.20])
 tx=list(loc.get('tx'));tx[12:15]=loc.get('p');loc.set('tx',tx)
tree.append(good);pdx.write_meshfile(str(path),tree)
print('Corrected weapon locator container and transform translations; character mesh unchanged.')
