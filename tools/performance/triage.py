"""Snapshot the current project and inventory complete HOI4 error records."""
from pathlib import Path
import collections, datetime, hashlib, json, re, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
DOC = Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
OUT = ROOT / 'docs/performance/20261023'
POINTER = ROOT.parent / '.codex_backups/APDC/performance-current-backup.txt'

def inventory(path):
    text = path.read_text('utf-8-sig', errors='replace')
    records = re.split(r'(?=^\[\d\d:\d\d:\d\d\]\[)', text, flags=re.M)
    records = [r.strip() for r in records if r.strip()]
    counts = collections.Counter()
    samples = {}
    for rec in records:
        normalized = re.sub(r'^\[[^\]]*\]\[[^\]]*\]', '', rec)
        counts[normalized] += 1
        samples.setdefault(normalized, rec)
    result = {'path': str(path), 'bytes': path.stat().st_size, 'records': len(records),
              'unique': len(counts), 'groups': [
        {'count': n, 'message': key, 'sample': samples[key]}
        for key,n in counts.most_common()]}
    return result

def snapshot():
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT.parent / '.codex_backups/APDC' / (stamp + '-errors-performance')
    backup.mkdir(parents=True)
    manifest = {}
    for folder in ['common', 'events', 'history', 'interface', 'localisation', 'tools/economy', 'sound']:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file() or p.suffix.lower() not in ['.txt','.lua','.gui','.gfx','.asset','.yml','.py','.json']: continue
            rel = p.relative_to(ROOT)
            dest = backup/'original'/rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p,dest)
            manifest[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [ROOT/'descriptor.mod', ROOT/'AGENTS.md', ROOT.parent/'APDC.mod']:
        shutil.copy2(p, backup/('external-APDC.mod' if p.parent == ROOT.parent else p.name))
    for name,path in [('user',DOC/'logs'),('economy-qa',Path('D:/APDC_EconomyQA_20261023/logs'))]:
        if path.exists(): shutil.copytree(path,backup/'logs'/name)
    status = subprocess.run(['git','status','--porcelain=v1','-uall'], cwd=ROOT, capture_output=True).stdout
    (backup/'git-status.txt').write_bytes(status)
    (backup/'sha256.json').write_text(json.dumps(manifest,indent=2),'utf-8')
    POINTER.write_text(str(backup),'utf-8')
    return backup

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    if '--snapshot' in sys.argv:
        print('Backup:',snapshot())
    for name,path in [('user',DOC/'logs/error.log'),('economy-qa',Path('D:/APDC_EconomyQA_20261023/logs/error.log'))]:
        result=inventory(path)
        (OUT/(name+'-before.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        print(name, 'records',result['records'],'unique',result['unique'])
        for group in result['groups'][:28]: print(group['count'],group['message'][:300].replace('\n',' | '))
