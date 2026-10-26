"""Transactional, non-destructive installation; only exact staged files are targets."""
from pathlib import Path
import hashlib,json,shutil
from build_core import ROOT,WORK,STAGE

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    qa=json.loads((WORK/'staging_validation.json').read_text('utf8'))
    assert qa['status']=='PASS','Staging validation must pass first'
    backup=WORK/'backup';manifest=backup/'manifest.json'
    records=json.loads(manifest.read_text('utf8')) if manifest.exists() else {}
    pending=[]
    for src in sorted(STAGE.rglob('*')):
        if not src.is_file():continue
        rel=src.relative_to(STAGE);dst=ROOT/rel
        assert dst.resolve().is_relative_to(ROOT.resolve()) and rel.parts[0] in ('common','events','history','gfx','interface','localisation')
        data=src.read_bytes();key=rel.as_posix();existing=dst.read_bytes() if dst.exists() else None
        if existing==data:continue
        if key in records and existing is not None:
            assert digest(existing)==records[key]['installed_sha256'],f'User changed a previously installed file: {dst}'
        pending.append((src,dst,rel,data,existing))
    # Preflight all targets before performing any installation.
    backup.mkdir(parents=True,exist_ok=True)
    for src,dst,rel,data,existing in pending:
        key=rel.as_posix()
        if key not in records:
            record={'existed_before':existing is not None,'original_sha256':digest(existing) if existing else None}
            if existing is not None:
                saved=backup/'files'/rel;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(existing)
            records[key]=record
        records[key]['installed_sha256']=digest(data)
        dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        # Persist after each file, so an interrupted run remains auditable/recoverable.
        manifest.write_text(json.dumps(records,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({'installed_or_updated':len(pending),'backed_up_existing':sum(v['existed_before'] for v in records.values()),'new_files':sum(not v['existed_before'] for v in records.values()),'manifest':str(manifest)},ensure_ascii=False))

if __name__=='__main__':main()
