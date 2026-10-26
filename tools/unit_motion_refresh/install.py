"""Scoped install with original backups and conflict protection."""
from common import *
import shutil
assert (WORK/'roundtrip_validation.json').exists(),'Run roundtrip verification first'
qa=json.loads((WORK/'roundtrip_validation.json').read_text('utf8'));assert qa['status']=='PASS'
static=json.loads((WORK/'static_validation.json').read_text('utf8'));assert static['status']=='PASS'
for rel,digest in static['files_sha256'].items():assert sha(STAGE/rel)==digest,('Staging changed since validation',rel)
manifest=WORK/'backup/manifest.json';records=json.loads(manifest.read_text('utf8')) if manifest.exists() else {}
basepath=ROOT/'art_source/unit_overhaul/backup/manifest.json';base=json.loads(basepath.read_text('utf8'))
pending=[]
for source in sorted(STAGE.rglob('*')):
 if not source.is_file():continue
 rel=source.relative_to(STAGE);key=rel.as_posix();assert rel.parts[0]=='gfx';dest=ROOT/rel;new=sha(source)
 if dest.exists() and sha(dest)==new:continue
 if dest.exists():
  expected=records.get(key,base.get(key,{})).get('installed_sha256')
  assert expected is not None and sha(dest)==expected,('Concurrent or untracked edit',key)
 pending.append((source,rel,dest,new))
for source,rel,dest,new in pending:
 key=rel.as_posix()
 if key not in records:
  records[key]={'existed_before':dest.exists(),'original_sha256':sha(dest) if dest.exists() else None}
  if dest.exists():
   saved=WORK/'backup/files'/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
 mirror=ROOT/'art_source/unit_overhaul/staging'/rel;mirror.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,mirror)
 records[key]['installed_sha256']=new
 if key not in base:base[key]={'existed_before':False,'original_sha256':None}
 base[key]['installed_sha256']=new
 save_json(manifest,records);save_json(basepath,base)
save_json(WORK/'install_report.json',{'installed':True,'updated_files':len(pending),'backup':str(manifest.parent),'scope':'gfx only','runtime_tested':False})
print('INSTALLED',len(pending),flush=True)
