"""Shared deterministic generators and byte-preserving change backups."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
DATA = ROOT / 'tools/parliament/data'
REPORT = ROOT / 'docs/parliament/20261107-implementation'
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse, walk, patches

PARTIES = ['communism','socialism','social_democracy','liberalism','conservatism','authoritarianism','dictatorship','fascism','fundamentalism']
NAMES = ['先锋社会主义','广泛社会主义','社会民主主义','自由主义','保守主义','威权主义','独裁制','法西斯主义','原教旨主义']
COLORS = ['A20606','E03964','E7B620','9A9A9A','183C9B','9A5800','6A6900','703C04','450C90']
P = 'apdc_parl_'
BACKUP = None
MANIFEST = {}
PARAMETERS = {'ROLE','KIND','TARGET','OPTION','ID','MONTHS','NAME','VALUE','COST','DESC','AVAILABLE'}


def lower_parameters(text):
    """HOI4 effects use variable arguments, not EU/Stellaris $parameters$.

    The generator accepts a concise authoring notation, then lowers every
    invocation to temporary inputs followed by effect=yes. Shipped files never
    contain parameterized-effect calls or unresolved $PARAM$ values.
    """
    edits=[]
    for n in walk(parse(text)):
        if not n.key.startswith(P) or not n.children or not all(c.key in PARAMETERS and c.value is not None for c in n.children):
            continue
        lines=[]
        for child in n.children:
            value=child.value.strip('"')
            if child.key in ('NAME','DESC') and not value.startswith(('$','token:',P+'arg_')):
                value='token:'+value
            lines.append('set_temp_variable = { '+P+'arg_'+child.key+' = '+value+' }')
        lines.append(n.key+' = yes')
        edits.append((n.start,n.end,'\n'.join(lines)))
    text=patches(text,edits)
    import re
    def quoted(match):
        result=match.group()
        for key in PARAMETERS:
            result=result.replace('$'+key+'$','[?'+P+'arg_'+key+('.GetTokenKey' if key in ('NAME','DESC') else '')+']')
        return result
    text=re.sub(r'"(?:\\.|[^"\\])*"',quoted,text)
    for key in PARAMETERS:
        text=text.replace('token:$'+key+'$',P+'arg_'+key)
        text=text.replace('$'+key+'$',P+'arg_'+key)
    return text


def begin(backup=None):
    global BACKUP, MANIFEST
    if backup:
        BACKUP = Path(backup).resolve()
    else:
        stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')
        BACKUP = ROOT.resolve().parent / '.codex_backups/APDC' / (stamp+'-parliament-implementation')
    BACKUP.mkdir(parents=True, exist_ok=True)
    manifest = BACKUP / 'changes.json'
    MANIFEST = json.loads(manifest.read_text('utf-8')) if manifest.exists() else {}
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT/'backup.json').write_text(json.dumps({'backup':str(BACKUP)},ensure_ascii=False,indent=2),encoding='utf-8')
    return BACKUP


def remember(path):
    path = Path(path)
    rel = path.relative_to(ROOT).as_posix()
    if BACKUP is None:
        raise RuntimeError('Call begin before writing')
    if rel not in MANIFEST:
        entry = {'existed': path.exists()}
        if path.exists():
            original = path.read_bytes()
            entry['sha256_before'] = hashlib.sha256(original).hexdigest()
            dest = BACKUP/'files'/rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(original)
        MANIFEST[rel] = entry
    return rel


def write(rel, content, bom=False):
    path = ROOT/rel
    if isinstance(content,str) and path.suffix in ('.txt','.gui','.gfx') and not str(rel).startswith('tools/parliament/legacy/'):
        content=lower_parameters(content)
    data = content if isinstance(content, bytes) else content.encode('utf-8-sig' if bom else 'utf-8')
    if path.exists() and path.read_bytes() == data:
        return
    key = remember(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    MANIFEST[key]['sha256_after'] = hashlib.sha256(data).hexdigest()
    (BACKUP/'changes.json').write_text(json.dumps(MANIFEST,ensure_ascii=False,indent=2),encoding='utf-8')


def json_write(rel, value):
    write(rel, json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def read(rel):
    return (ROOT/rel).read_text('utf-8-sig')


def block(key, body):
    return key+' = {\n'+body+'\n}\n'


def sv(name, value):
    if isinstance(value,float):
        value=format(value,'.5f').rstrip('0').rstrip('.') or '0'
    return 'set_variable = { '+P+name+' = '+str(value)+' }\n'


def var(name):
    return P+name


def ck(name, op, value):
    if op in ('>=','<=','!='):
        return 'NOT = { '+ck(name,{'<=':'>','>=':'<','!=':'='}[op],value)+' }'
    return 'check_variable = { '+var(name)+' '+op+' '+str(value)+' }'


def op(name, operation, value):
    prefix={'add':'add_to','subtract':'subtract_from','multiply':'multiply','divide':'divide','mod':'modulo'}[operation]
    return prefix+'_variable = { '+var(name)+' = '+str(value)+' }\n'


def clamp(name, low, high):
    return 'clamp_variable = { var = '+var(name)+((' min = '+str(low)) if low is not None else '')+((' max = '+str(high)) if high is not None else '')+' }\n'


def iff(test, body, otherwise=''):
    s=block('if','limit = { '+test+' }\n'+body)
    return s+(block('else',otherwise) if otherwise else '')


def floor(name):
    return sv('floor_original',var(name))+'round_variable = '+var(name)+'\n'+iff(ck(name,'>',var('floor_original')),op(name,'subtract',1))


def effect(name, body):
    return block(P+name,body)


def load_json(name):
    return json.loads((DATA/name).read_text('utf-8'))


def loc_write(entries):
    lines=['l_simp_chinese:']
    for key,value in entries.items():
        value=value.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
        lines.append(' '+key+':0 "'+value+'"')
    write('localisation/simp_chinese/apdc_parliament_l_simp_chinese.yml','\n'.join(lines)+'\n',True)
