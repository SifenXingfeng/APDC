"""Report exact pre-existing file changes and validate generated references."""
import json,hashlib,re
from PIL import Image
from common import *

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 backup=Path((ROOT.parent/'.codex_backups/APDC/economy-current-backup.txt').read_text('utf-8-sig').strip())
 changes=[]; migrations=[]; errors=[]
 maintenance_log=ROOT/'docs/performance/20261023/repairs.json'
 intentional_deletions={x['path'] for x in json.loads(maintenance_log.read_text('utf-8')) if x['after'] is None} if maintenance_log.exists() else set()
 for old in (backup/'project').rglob('*'):
  if not old.is_file():continue
  rel=old.relative_to(backup/'project');current=ROOT/rel
  if not current.exists():
   if rel.as_posix() not in intentional_deletions:errors.append('Removed backed-up file: '+str(rel))
   continue
  if digest(old)==digest(current):continue
  changes.append(str(rel))
  s=old.read_text('utf-8-sig');t=current.read_text('utf-8-sig')
  if re.search(r'\bconsumer_goods_(factor|expected_value)\s*=',s):
   migrations.append({'file':str(rel),'old_sha256':digest(old),'current_sha256':digest(current),'factory_factors':len(re.findall(r'\bconsumer_goods_factor\s*=',s)),'expected_factors':len(re.findall(r'\bconsumer_goods_expected_value\s*=',s))})
 # The events replace_path makes project events the complete effective set.
 # No matching event keys were present in this task's migration.
 event_keys=[str(p.relative_to(ROOT)) for p in (ROOT/'events').rglob('*.txt') if 'APDC_eco_population_factor' in p.read_text('utf-8-sig')]
 for folder in ['common','interface','localisation']:
  for p in (ROOT/folder).rglob('*APDC_economy*'):
   if not p.is_file():continue
   if p.suffix in ['.txt','.gui','.gfx']:
    try:parse(p.read_text('utf-8-sig'))
    except Exception as e:errors.append(str(p.relative_to(ROOT))+': '+str(e))
    if p.read_bytes().startswith(b'\xef\xbb\xbf'):errors.append('Script BOM: '+str(p))
   if p.suffix=='.yml':
    if not p.read_bytes().startswith(b'\xef\xbb\xbf'):errors.append('Localization missing BOM: '+str(p))
 catalogue=json.loads((WORK/'equipment_catalogue.json').read_text('utf-8'))
 econ=parse((ROOT/'common/ideas/_economic.txt').read_text('utf-8-sig'))[0]
 for law,expected in [('free_trade',.8),('export_focus',.5),('limited_exports',.25),('closed_economy',0)]:
  matches=[x for cat in econ.children for x in cat.children if x.key==law]
  if len(matches)!=1 or not matches[0].get('modifier') or float(matches[0].get('modifier').val('APDC_eco_consumer_trade_freedom','-1'))!=expected:errors.append('Incorrect consumer trade freedom: '+law)
 for p in (ROOT/'common/scripted_effects').glob('APDC_economy*.txt'):
  if re.search(r'(?<![\w.])\d+\.\d{9,}',p.read_text('utf-8-sig')):errors.append('Unsafe long fixed-point literal: '+p.name)
 gfx_names=set()
 for base in [GAME/'interface',ROOT/'interface']:
  for p in base.rglob('*.gfx'):
   gfx_names.update(re.findall(r'\bname\s*=\s*"?(GFX_[A-Za-z0-9_]+)',p.read_text('utf-8-sig',errors='replace')))
 gui=(ROOT/'interface/APDC_economy_panel.gui').read_text('utf-8-sig')
 for name in set(re.findall(r'(?:spriteType|quadTextureSprite)\s*=\s*"([^"]+)"',gui)):
  if name not in gfx_names:errors.append('Missing GUI sprite: '+name)
 for top in parse((ROOT/'interface/APDC_economy_panel.gfx').read_text('utf-8-sig')):
  for sprite in top.children:
   path=sprite.val('texturefile');frames=int(sprite.val('noOfFrames','1'))
   if not path:continue
   p=ROOT/path
   if not p.exists():errors.append('Missing economy texture: '+path)
   else:
    with Image.open(p) as im:
     if im.width%frames:errors.append('Invalid horizontal frame dimensions: '+path)
 for e in catalogue:
  if any(x.startswith('NOR_') for x in e['modules'].values()):errors.append('Exclusive preset: '+e['id'])
  if e['cost']<=0:errors.append('Invalid cost: '+e['id'])
 native=[]
 replaces=re.findall(r'replace_path\s*=\s*"([^"]+)"',(ROOT/'descriptor.mod').read_text('utf-8-sig'))
 for p in (GAME/'common').rglob('*.txt'):
  rel=p.relative_to(GAME)
  if (ROOT/rel).exists() or any(str(rel).replace('\\','/').startswith(r+'/') for r in replaces):continue
  s=p.read_text('utf-8-sig',errors='replace')
  if re.search(r'\bconsumer_goods_(factor|expected_value)\s*=',s):native.append(str(rel))
 result={'changed_existing_files':changes,'migration':migrations,'event_migrations':event_keys,'native_consumer_fallthrough':native,'validation_errors':errors,'catalogue_count':len(catalogue)}
 (WORK/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({'changed_existing_files':len(changes),'migrated_files':len(migrations),'events':event_keys,'native_fallthrough_files':len(native),'errors':errors},ensure_ascii=False))
 if errors:raise SystemExit(1)

if __name__=='__main__':main()
