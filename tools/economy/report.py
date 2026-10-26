"""Snapshot runtime evidence; never convert a partial run into a passing one."""
import datetime,hashlib,json,re
from common import *
from runtime import QA

def main():
 logs={n:(QA/'logs'/n).read_text('utf-8-sig',errors='replace') for n in ['game.log','error.log','system.log']}
 tests=re.findall(r'APDC_ECO_ASSERT (PASS|FAIL) ([A-Za-z0-9_]+)',logs['game.log'])
 failures=sorted({name for status,name in tests if status=='FAIL'})
 passed=sorted({name for status,name in tests if status=='PASS'})
 related=re.compile(r'APDC_eco|APDC_economy|common/ideas/_economic\.txt|APDC_economic_system',re.I)
 errors=[l for l in logs['error.log'].splitlines() if related.search(l)]
 day=[l for l in logs['game.log'].splitlines() if 'APDC_ECO_QA DAY' in l]
 saves=[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (QA/'save games').glob('*.hoi4')]
 audit=json.loads((WORK/'audit.json').read_text('utf-8'))
 files=set(audit['changed_existing_files'])|set(json.loads((WORK/'native_modifier_overrides.json').read_text('utf-8')))
 for folder in ['common','interface','localisation','gfx/interface/APDC/economy','tools/economy']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in str(p) and ('APDC_economy' in p.name or 'tools/economy' in p.as_posix() or 'gfx/interface/APDC/economy' in p.as_posix()):files.add(str(p.relative_to(ROOT)))
 hashes={str(rel):hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sorted(files)}
 result={
  'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'project':str(ROOT),'profile':str(QA),
  'backup':(ROOT.parent/'.codex_backups/APDC/economy-current-backup.txt').read_text('utf-8-sig').strip(),
  'process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),
  'silent_window_audit':json.loads((WORK/'silent_verification.json').read_text('utf-8-sig')),
  'active_dlcs':re.findall(r'Active DLC: (.+)',logs['system.log']),
  'active_mods':re.findall(r'Active Mod: (.+)',logs['system.log']),
  'last_daily_snapshot':day[-1] if day else None,
  'last_game_datetime':re.findall(r'\[(\d{4}\.\d{2}\.\d{2}\.\d{2})\]',day[-1])[-1] if day else None,
  'passed_assertions':passed,'failed_assertions':failures,
  'economy_error_lines':errors,'economy_error_count':len(errors),
  'static_validation_errors':audit['validation_errors'],
  'autosaves':saves,'source_sha256':hashes,
  'native_modifier_provenance':{rel:{'native_sha256':hashlib.sha256((GAME/rel).read_bytes()).hexdigest(),'project_sha256':hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()} for rel in json.loads((WORK/'native_modifier_overrides.json').read_text('utf-8'))},
  'user_decisions':{'occupation_garrison_maintenance':'Excluded per user decision on 2026-10-23; active army/navy/air and training remain billed.'},
  'validation_limits':['No foreground interaction or game screenshot visual acceptance was performed.','Other pre-existing, unrelated project errors remain in the complete engine log.'],
  'all_recorded_behavioral_assertions_passed':bool(tests) and not failures,
 }
 (WORK/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
 print(json.dumps({'assertions_passed':len(passed),'assertions_failed':failures,'economy_errors':len(errors),'active_dlcs':len(result['active_dlcs']),'last_daily_snapshot':result['last_daily_snapshot']},ensure_ascii=False))
 if failures or errors or audit['validation_errors']:raise SystemExit(1)

if __name__=='__main__':main()
