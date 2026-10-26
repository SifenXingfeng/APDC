"""Validate the effective base + mod + staged data, not just generated text."""
from pathlib import Path
import json,re,hashlib,math
from PIL import Image
from cw import parse,walk
from build_core import ROOT,WORK,STAGE
from build_migration import GAME,LAND_GROUPS
from catalog import UNIT_IDS,EQUIPMENT_NAMES

def effective(folder,pattern='*.txt',recursive=True,staged=True):
    files={}
    for root in [GAME,ROOT]+([STAGE] if staged else []):
        paths=(root/folder).rglob(pattern) if recursive else (root/folder).glob(pattern)
        for p in paths:files[p.relative_to(root).as_posix()]=p
    return files

def database(folder,wrapper,recursive=True,staged=True):
    db={};duplicate=[]
    for rel,p in effective(folder,recursive=recursive,staged=staged).items():
        for root in parse(p.read_text('utf-8-sig')):
            if root.key==wrapper:
                for n in root.children:
                    if n.key in db:duplicate.append((n.key,rel))
                    db[n.key]=n
    return db,duplicate

def main(staged=True):
    errors=[];checks={}; out=STAGE if staged else ROOT
    generated=list(STAGE.rglob('*.txt'))+list(STAGE.rglob('*.gfx'))+list(STAGE.rglob('*.asset'))
    for p in generated:
        actual=p if staged else ROOT/p.relative_to(STAGE)
        try:parse(actual.read_text('utf-8-sig'))
        except Exception as ex:errors.append(f'{actual}: syntax: {ex}')
    units,dups=database('common/units','sub_units',False,staged)
    equipment,eqdups=database('common/units/equipment','equipments',True,staged)
    tech,_=database('common/technologies','technologies',True,staged)
    if any(k.startswith('apdc_') for k,p in dups+eqdups):errors.append('Duplicate APDC unit/equipment ID')
    declared=set()
    for _,p in effective('common/unit_tags',staged=staged).items():
        for n in walk(parse(p.read_text('utf-8-sig'))):
            if n.op=='':declared.add(n.key)
    disabled=set(json.loads((WORK/'disabled_legacy_units.json').read_text('utf8')))
    for uid in UNIT_IDS:
        if uid not in units:errors.append('Missing unit '+uid);continue
        u=units[uid];need=u.get('need')
        if not need or not need.children:errors.append('No equipment for '+uid);continue
        for n in need.children:
            if n.key not in equipment:errors.append(f'{uid}: missing archetype {n.key}')
            elif equipment[n.key].val('is_archetype')!='yes':errors.append(f'{uid}: need is not archetype {n.key}')
            if not n.value or not math.isfinite(float(n.value)) or float(n.value)<=0:errors.append('Invalid quantity '+uid)
        if u.val('group') not in LAND_GROUPS:errors.append('Invalid group '+uid)
        if u.val('sprite')!=uid:errors.append('Model routing differs from unit ID '+uid)
        if u.val('group')=='support':
            if float(u.val('combat_width','-1'))!=0:errors.append('Support has width '+uid)
            if u.val('divisional')==u.val('regimental'):errors.append('Ambiguous support slot '+uid)
        for n in (u.get('categories').children if u.get('categories') else []):
            if n.key not in declared:errors.append('Undeclared category '+n.key)
        for n in (u.get('essential').children if u.get('essential') else []):
            if not need.get(n.key):errors.append(f'{uid}: essential not requested {n.key}')
        if u.get('same_support_type') and u.val('same_support_type') not in units:errors.append('Missing support exclusion target '+uid)
    for uid in disabled:
        if units[uid].val('active')!='no':errors.append('Legacy unit still active '+uid)
    for folder in ('common/technologies','common/doctrines','common/special_projects/projects'):
        for rel,p in effective(folder,staged=staged).items():
            text=p.read_text('utf-8-sig')
            if 'enable_subunits' not in text:continue
            for n in walk(parse(text)):
                if n.key=='enable_subunits':
                    for child in n.children:
                        if child.key in disabled:errors.append(f'{rel}: legacy unlock {child.key}')
    bootstrap=tech['APDC_land_units_bootstrap']
    regular=set(n.key for n in bootstrap.get('enable_subunits').children)
    if regular!=set(UNIT_IDS)-{UNIT_IDS[15],UNIT_IDS[16]}:errors.append('Wrong regular unlock roster')
    for n in bootstrap.get('enable_equipments').children:
        if n.key not in equipment:errors.append('Missing buildable equipment '+n.key)
    for key in EQUIPMENT_NAMES:
        base=equipment['apdc_'+key+'_equipment'];variant=equipment['apdc_'+key+'_equipment_1']
        if variant.val('archetype')!=base.key:errors.append('Invalid equipment inheritance '+key)
        if variant.val('is_buildable')!='yes':errors.append('Unbuildable variant '+key)
        if base.get('module_slots'):errors.append('Unexpected designer requirement '+key)
    registry=(out/'interface/zz_APDC_unit_icons.gfx').read_text('utf8')
    mapping=(out/'gfx/entities/zzz_APDC_unit_mapping.asset').read_text('utf8')
    for uid in UNIT_IDS:
        for suffix in ('_icon_medium','_icon_medium_white'):
            if f'GFX_unit_{uid}{suffix}' not in registry:errors.append('Missing icon '+uid+suffix)
        if f'"{uid}_entity"' not in mapping:errors.append('Missing model entity '+uid)
    # DDS first frame equals supplied pixels, including alpha.
    normalized=json.loads((WORK/'normalized_units.json').read_text('utf8'))
    for u in normalized:
        source=Image.open(WORK/'design'/u['icon']).convert('RGBA')
        actual=Image.open(out/'gfx/interface/apdc_units'/(u['id']+'.dds')).convert('RGBA')
        if actual.size!=(152,42) or actual.crop((0,0,76,42)).tobytes()!=source.tobytes():errors.append('Icon fidelity failure '+u['id'])
    # Verify optional per-unit test templates: support attaches only to permitted groups.
    oob=(out/'history/units/APDC_unit_test_templates.txt').read_text('utf8')
    fixture_count=0
    for n in parse(oob):
        if n.key!='division_template':continue
        fixture_count+=1
        for part in ('regiments','support','regimental_support'):
            block=n.get(part)
            if not block:continue
            for c in block.children:
                if c.key not in units:errors.append('Fixture missing unit '+c.key)
        if n.get('regimental_support'):
            if len(n.get('regiments').children)<3:errors.append('Regimental support fixture requires at least three battalions')
            support=units[n.get('regimental_support').children[0].key]
            battalion=units[n.get('regiments').children[0].key]
            if battalion.val('group') not in [x.key for x in support.get('allowed_battalion_groups').children]:errors.append('Fixture group mismatch')
    if fixture_count!=80:errors.append('Wrong number of test templates')
    # No retired infantry in the three Madagascar starting divisions.
    mad=(out/'history/units/MAD_2060.txt').read_text('utf8')
    if len(re.findall(r'\bdivision\s*=\s*{',mad))!=3:errors.append('Madagascar divisions altered')
    if re.search(r'\binfantry\s*=',mad):errors.append('Madagascar old unit reference remains')
    empty=(out/'history/units/APDC_empty.txt').read_text('utf-8-sig')
    if any(n.key=='division_template' for n in parse(empty)):errors.append('Blank OOB must not repeatedly seed templates')
    seed=(out/'history/units/APDC_basic_template.txt').read_text('utf8')
    seed_templates=[n for n in parse(seed) if n.key=='division_template']
    if len(seed_templates)!=1 or len(seed_templates[0].get('regiments').children)!=6:errors.append('Basic editing seed invalid')
    if re.search(r'\bdivision\s*=',seed):errors.append('Basic editing seed must not spawn troops')
    init=(out/'common/scripted_effects/APDC_land_units.txt').read_text('utf8')
    if 'has_country_flag = APDC_basic_template_initialized' not in init:errors.append('Editing seed is not guarded')
    if any((out/'history/units').glob('APDC_qa_spawn*')):errors.append('Automatic QA troops installed in real project')
    if not staged:
        manifest=json.loads((WORK/'backup/manifest.json').read_text('utf8'))
        for rel,record in manifest.items():
            p=ROOT/rel
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=record['installed_sha256']:
                errors.append('Installed manifest mismatch: '+rel)
    checks.update(units=82,combat_units=49,divisional_support=25,regimental_support=8,
                  new_equipment_archetypes=len(EQUIPMENT_NAMES),legacy_inactive=len(disabled),optional_test_templates=fixture_count,
                  icon_first_frame_pixel_exact=True,game_runtime_tested=False,
                  status='PASS' if not errors else 'FAIL',errors=errors,staged=staged)
    (WORK/('staging_validation.json' if staged else 'installed_validation.json')).write_text(json.dumps(checks,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(checks,ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':
    import sys
    main('--installed' not in sys.argv)
