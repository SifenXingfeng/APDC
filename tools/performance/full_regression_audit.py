"""Read-only inventory of the complete cleanup batch, using pre-task provenance.

Never use the mutable original/ folder alone to decide whether a file existed:
later native overrides were also copied there. Initial hashes and first edit
records distinguish APDC files from native fallthrough and newly created data.
"""
from pathlib import Path
import collections, difflib, hashlib, json, re, sys

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
BEFORE = ROOT.parent / '.codex_backups/APDC/20261023-101028-errors-performance'
OUT = ROOT / 'docs/performance/20261023-full-regression-audit'
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse, walk


def load(p):
    return json.loads(p.read_text('utf-8-sig'))


INITIAL = load(BEFORE / 'sha256.json')
EDITS = load(ROOT / 'docs/performance/20261023/repairs.json')
FIRST = {}
for row in EDITS:
    FIRST.setdefault(row['path'], row)
_DLC_SOURCES = None


def source_before(rel):
    global _DLC_SOURCES
    original = BEFORE / 'original' / rel
    expected = INITIAL.get(rel)
    if expected or FIRST.get(rel, {}).get('before'):
        if original.exists():
            if expected and hashlib.sha256(original.read_bytes()).hexdigest() != expected:
                raise ValueError('Initial snapshot mismatch: ' + rel)
            return original
        raise ValueError('Missing original bytes: ' + rel)
    native = GAME / rel
    if native.exists():
        return native
    if _DLC_SOURCES is None:
        _DLC_SOURCES = {}
        for bundle in ['dlc', 'integrated_dlc']:
            for package in (GAME / bundle).iterdir():
                if not package.is_dir():
                    continue
                for prefix in ['common', 'interface', 'localisation', 'music']:
                    folder = package / prefix
                    if folder.exists():
                        for p in folder.rglob('*'):
                            if p.is_file():
                                _DLC_SOURCES[p.relative_to(package).as_posix()] = p
    return _DLC_SOURCES.get(rel)


def signature(n):
    return (n.key, n.op, n.value, tuple(signature(c) for c in n.children))


def root_id(n):
    return n.val('name') if n.key == 'defined_text' else n.key


def run():
    OUT.mkdir(exist_ok=True)
    files = {}
    for manifest in ['20261023/final-changes.json',
                     '20261023-weekly-economy/final-changes.json',
                     '20261023-core-regression/repairs.json']:
        for row in load(ROOT / 'docs/performance' / manifest):
            files.setdefault(row['path'], {})
    diffs = OUT / 'diffs'
    diffs.mkdir(exist_ok=True)
    for rel in sorted(files):
        before = source_before(rel)
        current = ROOT / rel
        a = before.read_bytes() if before else b''
        b = current.read_bytes() if current.exists() else b''
        row = files[rel]
        row.update({'before_source': str(before) if before else None,
                    'before_sha256': hashlib.sha256(a).hexdigest() if before else None,
                    'current_sha256': hashlib.sha256(b).hexdigest() if current.exists() else None,
                    'before_bytes': len(a), 'current_bytes': len(b),
                    'reasons': sorted({x['reason'] for x in EDITS if x['path'] == rel})})
        if current.suffix not in ['.txt', '.gui', '.gfx', '.lua', '.yml', '.py']:
            row['kind'] = 'binary'
            continue
        sa, sb = (x.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '') for x in [a, b])
        patch = ''.join(difflib.unified_diff(sa.splitlines(True), sb.splitlines(True),
                                           fromfile='before/' + rel, tofile='current/' + rel))
        dest = diffs / (rel.replace('/', '__') + '.diff')
        dest.write_text(patch, 'utf-8')
        row['diff'] = dest.relative_to(ROOT).as_posix()
        row['kind'] = 'text'
        if current.suffix in ['.txt', '.gui', '.gfx']:
            try:
                old_nodes, new_nodes = parse(sa), parse(sb)
                old_roots = collections.Counter(root_id(n) for n in old_nodes)
                new_roots = collections.Counter(root_id(n) for n in new_nodes)
                row['removed_roots'] = list((old_roots - new_roots).elements())
                row['added_roots'] = list((new_roots - old_roots).elements())
                row['semantic_equal'] = tuple(map(signature, old_nodes)) == tuple(map(signature, new_nodes))
            except Exception as exc:
                row['before_or_current_parse_error'] = str(exc)
    (OUT / 'complete-inventory.json').write_text(json.dumps(files, ensure_ascii=False, indent=2), 'utf-8')
    summary = {'paths': len(files), 'kinds': dict(collections.Counter(r['kind'] for r in files.values())),
               'parse_errors': {p: r['before_or_current_parse_error'] for p, r in files.items()
                                if 'before_or_current_parse_error' in r},
               'limitations': 'Inventory and structural differences; individual dispositions and validations are separate.'}
    (OUT / 'inventory-summary.json').write_text(json.dumps(summary, indent=2), 'utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    run()
