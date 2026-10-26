"""Install only the validated infantry rebind; preserve rollback and integration manifests."""
from pathlib import Path
import hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[2];WORK=ROOT/'art_source/infantry_vanilla_rig';STAGE=WORK/'staging'
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse
def sha(data):return hashlib.sha256(data).hexdigest()
report=json.loads((WORK/'validation.json').read_text('utf8'))
assert report['vanilla_bind_data_exact'] and report['mesh_reimported'] and len(report['sampled_animation_checks'])==27
assert not report.get('preview_only',False)
mesh=STAGE/'gfx/models/units/APDC_vanilla_infantry/APDC_vanilla_infantry.mesh'
assert (WORK/'validation.json').stat().st_mtime>=mesh.stat().st_mtime,'Revalidate after rebuilding the mesh'
if 'mesh_sha256' in report:assert report['mesh_sha256']==sha(mesh.read_bytes())
backup=WORK/'backup';backup.mkdir(exist_ok=True)
manifest_path=backup/'manifest.json';records=json.loads(manifest_path.read_text('utf8')) if manifest_path.exists() else {}
base_manifest_path=ROOT/'art_source/unit_overhaul/backup/manifest.json'
base_records=json.loads(base_manifest_path.read_text('utf8'))
pending=[]
for path in sorted(STAGE.rglob('*')):
 if not path.is_file():continue
 rel=path.relative_to(STAGE);assert rel.parts[0]=='gfx'
 dest=ROOT/rel;data=path.read_bytes();existing=dest.read_bytes() if dest.exists() else None
 if existing==data:continue
 key=rel.as_posix()
 if existing is not None:
  expected=records.get(key,{}).get('installed_sha256') or base_records.get(key,{}).get('installed_sha256')
  assert expected and sha(existing)==expected,('Concurrent edit or unknown target',key)
 if path.suffix in ('.asset','.gfx'):parse(data.decode('utf-8-sig'))
 pending.append((path,rel,dest,data,existing))
for path,rel,dest,data,existing in pending:
 key=rel.as_posix()
 if key not in records:
  records[key]={'existed_before':existing is not None,'original_sha256':sha(existing) if existing else None}
  if existing is not None:
   saved=backup/'files'/rel;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(existing)
 records[key]['installed_sha256']=sha(data)
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 mirror=ROOT/'art_source/unit_overhaul/staging'/rel;mirror.parent.mkdir(parents=True,exist_ok=True);mirror.write_bytes(data)
 if key not in base_records:base_records[key]={'existed_before':False,'original_sha256':None}
 base_records[key]['installed_sha256']=sha(data)
 manifest_path.write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf8')
 base_manifest_path.write_text(json.dumps(base_records,ensure_ascii=False,indent=2),'utf8')
report['installed']=True
(WORK/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps({'updated_files':len(pending),'backup':str(backup),'original_game_files_modified':False},ensure_ascii=False))
