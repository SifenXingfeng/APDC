"""Compile the reviewed design into a staged, auditable first integration."""
from pathlib import Path
import re, json
from collections import OrderedDict
from catalog import UNIT_IDS, EQUIPMENT_ALIASES, EQUIPMENT_NAMES, BASELINES, LEGACY_MAP
from cw import render, parse, walk

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'art_source/unit_overhaul'
STAGE = WORK/'staging'
SOURCE = json.loads((WORK/'design/units_source.json').read_text('utf-8'))
NOTES = []

def emit(rel, text, bom=False):
    path = STAGE/rel
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8-sig' if bom else 'utf-8',newline='\n')

def number(text):
    m = re.match(r'\s*([+-]?[\d,]+(?:\.\d+)?)',text)
    if not m: raise ValueError(f'Not a number: {text!r}')
    return float(m[1].replace(',','')) if '.' in m[1] else int(m[1].replace(',',''))

def identifiers(text):
    return re.findall(r'(?<![A-Za-z0-9_])[a-z][a-z0-9_]*(?![A-Za-z0-9_])',text)

def eq(text):
    cleaned = re.sub(r'装备需求\s*[→：:]\s*|^need\.', '',text).strip()
    tokens = identifiers(cleaned)
    candidates = tokens + [re.split(r'[（(]',cleaned)[0].strip()]
    for label in candidates:
        if label in EQUIPMENT_ALIASES:
            value = EQUIPMENT_ALIASES[label]
            return value if value.endswith('_equipment') else 'apdc_'+value+'_equipment'
    raise ValueError(f'Unknown equipment label: {text}')

def eq_list(text):
    return list(dict.fromkeys(eq(t) for t in re.split(r'[;；]',text) if t.strip()))

def category(text):
    values = re.findall(r'category_[a-z0-9_]+',text)
    if '自律机械' in text: values.append('category_apdc_robots')
    if '自律人形' in text: values.append('category_apdc_dolls')
    return list(dict.fromkeys(values))

CORE = {'生命值（HP）':'max_strength','组织度':'max_organisation','基础恢复率':'default_morale',
        '战斗宽度':'combat_width','人力':'manpower','训练时间（天）':'training_time',
        '补给消耗':'supply_consumption','镇压值':'suppression'}
TERRAINS = {'forest','hills','mountain','jungle','marsh','plains','desert','river','amphibious','urban','fort'}
BOOLS = {'active','special_forces','mountaineers','marines','rangers','can_be_parachuted',
         'regimental','divisional','affects_speed','is_artillery_brigade'}
SCALARS = {'priority','ai_priority','combat_width','manpower','max_strength','max_organisation','default_morale',
 'training_time','suppression','weight','supply_consumption','soft_attack','hard_attack','ap_attack','air_attack',
 'armor_value','defense','breakthrough','recon','maximum_speed','entrenchment','initiative',
 'supply_consumption_factor','fuel_consumption_factor','casualty_trickleback','experience_loss_factor',
 'own_equipment_fuel_consumption_mult','reliability_factor','equipment_capture_factor','suppression_factor'}

def build_unit(source):
    index = source['index']; uid = UNIT_IDS[index-1]
    name = re.split(r'[（(]',source['title'].lstrip('*'))[0].strip().rstrip('：:')
    if index == 16: name = '摩托化柳芭老妈'
    if index == 17: name = 'UMP姐妹骑兵'
    if index == 53: name = '蛙人部队（水域渗透）'
    if index == 67: name = '机甲连（AA02类机甲）'
    if index >= 75: name = '团级'+name
    if index in range(69,75): name = '师级'+name
    data = OrderedDict(); needs = OrderedDict(); mults = []; multi = None; indexed = {}
    raw_active = None; raw_group = None
    for row in source['tables'][1][1:]:
        raw = row[1].splitlines()[-1].strip()
        value = row[2].strip()
        key = re.sub(r'\s+','',raw).replace('mrash.','marsh.')
        if not value or value in ('-','未定义'):
            continue
        # Equipment rows are recognized by section as well as a well-formed path.
        if raw.startswith(('need.', '装备需求')) or raw in EQUIPMENT_ALIASES or re.split(r'[（(]',raw)[0].strip() in EQUIPMENT_ALIASES:
            needs[eq(raw)] = number(value)
        elif key.startswith('battalion_mult'):
            m = re.fullmatch(r'battalion_mult(?:\[(\d+)\])?\.(\w+)',key)
            assert m, key
            idx, field = m.groups()
            if idx:
                if idx not in indexed:
                    indexed[idx]={};mults.append(indexed[idx])
                block=indexed[idx]
            else:
                if field == 'category' or multi is None:
                    multi={};mults.append(multi)
                block=multi
            if field=='category':
                cats=category(value); assert len(cats)==1,(name,value)
                block[field]=cats[0]
            elif field=='add': block[field]='yes' if 'yes' in value else 'no'
            else: block[field]=number(value)
        elif key in ('sprite','map_icon_category','abbreviation'):
            data[key]=identifiers(value)[0] if key!='abbreviation' else '"'+value+'"'
        elif key=='type':
            types=identifiers(value)
            if '战术人形' in value:
                types.insert(0,'motorized' if 30<=index<=32 else 'mechanized' if 33<=index<=41 else 'infantry')
            if '机械单位' in value: types.insert(0,'mechanized' if index in (42,43,49) else 'infantry')
            data[key]=list(dict.fromkeys(types))
        elif key=='group':
            raw_group=value
            # Vanilla's otherwise-unused towed-combat-support group becomes the automation group.
            # No unsupported new enum/type is injected into the engine.
            data[key]='combat_support' if '自动化' in value else identifiers(value)[0]
        elif key=='categories': data[key]=category(value)
        elif key=='allowed_battalion_groups':
            groups=identifiers(value)
            if '自动化' in value: groups.append('combat_support')
            data[key]=list(dict.fromkeys(groups))
        elif key=='essential': data[key]=eq_list(value)
        elif key=='transport': data[key]=eq(value)
        elif key=='same_support_type':
            old=identifiers(value)[0]; data[key]=LEGACY_MAP.get(old,old)
        elif key in BOOLS:
            ids=identifiers(value); assert ids and ids[0] in ('yes','no'),(name,key,value)
            data[key]=ids[0]
            if key=='active':raw_active=ids[0]
        elif key in SCALARS:data[key]=number(value)
        elif '.' in key and key.split('.')[0] in TERRAINS:
            terrain,field=key.split('.')
            assert field in ('attack','defence','movement'),key
            data.setdefault(terrain,{})[field]=number(value)
        else:raise ValueError((index,name,'UNHANDLED FIELD',raw,value))
    # The field table is authoritative; the summary fills genuinely absent attributes.
    for row in source['tables'][0][1:]:
        for j in (0,2):
            if row[j] in CORE and row[j+1] != '未定义':
                k=CORE[row[j]]; v=number(row[j+1])
                if k not in data:
                    data[k]=v; NOTES.append(f'{name}: {k} 从核心属性表补入 {v}。')
                elif data[k]!=v:
                    NOTES.append(f'{name}: 摘要 {k}={v} 与细表 {data[k]} 不同，采用细表。')
    assert needs and all(v>0 for v in needs.values()),(name,needs)
    data['need']=needs
    if index >= 50:
        data['combat_width']=0
        data['affects_speed']='no'
        data['divisional']='no' if index>=75 else 'yes'
        data['regimental']='yes' if index>=75 else 'no'
        data.setdefault('division_3d_model_priority',0)
    data['abbreviation']=data.get('abbreviation','"U%02d"'%index)
    data['sprite']=uid
    data['map_icon_category']='armored' if 'armor' in data['type'] else 'infantry'
    data['active']='no' # all unlocks go through one reproducible bootstrap technology
    if index in (16,17):data['ai_priority']=0
    data.setdefault('max_strength',1)
    # Normalize demonstrable copy/paste category errors, leaving combat numbers intact.
    if index in (45,72):
        data['type']=[t for t in data['type'] if t!='rocket']
        data['categories']=[c for c in data['categories'] if c!='category_rocket_artillery']
    if index in (49,75,76,79):
        data['type']=[t for t in data['type'] if t!='anti_tank']
        if 'artillery' not in data['type']:data['type'].append('artillery')
        data['categories']=[c for c in data['categories'] if c!='category_tank_destroyers']
        data['categories'].append('category_self_propelled_artillery')
    if index==81:
        data['categories']=[c for c in data['categories'] if c not in ('category_all_armor','category_self_propelled_anti_air','category_self_propelled_anti_air_regimental_support')]
        data['categories'].append('category_anti_air')
    if 27<=index<=41 or index==55:data['categories'].append('category_apdc_dolls')
    if index in (26,42,43,49,52,58,62,68,75):data['categories'].append('category_apdc_robots')
    if index in (15,67):data['categories'].append('category_apdc_elite_mechanical')
    data['categories']=list(dict.fromkeys(data['categories']+['category_apdc_units']))
    data['essential']=data.get('essential',list(needs))
    assert set(data['essential'])<=set(needs),(name,'essential mismatch')
    # Ensure supplemental combined-service equipment cannot reduce the line unit speed.
    if data.get('transport') and data['transport'] not in needs:raise ValueError((name,'missing transport'))
    pairs=list(data.items())+[('battalion_mult',b) for b in mults]
    text = '# '+name+' | source row '+str(index)+' | original active='+str(raw_active)+'\n'
    text += uid+' = {\n'+render(pairs,1)+'}\n'
    return {'id':uid,'name':name,'index':index,'raw_group':raw_group,'raw_active':raw_active,
            'data':data,'mults':mults,'icon':source['images'][0],'text':text}

def equipments():
    pairs=[]
    fields='maximum_speed soft_attack hard_attack ap_attack armor_value hardness defense breakthrough build_cost_ic fuel_consumption reliability'.split()
    armored={'mbt','light_tank','airborne_tank','tank_support','amphib_tank','atgm','spaag','spg','engineer_vehicle','aa02','doomsday_dog','mortar'}
    mechanized={'wheeled_mech','tracked_mech','amphib_mech','airborne_ifv','multipod','multipod_art'}
    motors={'truck_art','mlrs','missile','transport_helo','attack_helo','hovercraft'}
    for name, label in EQUIPMENT_NAMES.items():
        ident='apdc_'+name+'_equipment'
        types=['armor'] if name in armored else ['mechanized'] if name in mechanized else ['motorized'] if name in motors else ['infantry']
        if name in {'towed_gun','truck_art','spg','multipod_art','mortar'}:types.append('artillery')
        if name in {'mlrs','missile'}:types+=['artillery','rocket']
        if name=='atgm':types.append('anti_tank')
        if name=='spaag':types.append('anti_air')
        e={'year':2060,'is_archetype':'yes','is_buildable':'no','picture':'apdc_eq_'+name,
           'type':types,'group_by':'archetype','interface_category':'interface_category_land',
           **dict(zip(fields,BASELINES[name])),'air_attack':45 if name=='spaag' else 18 if name=='heavy_weapons' else 0,
           'lend_lease_cost':BASELINES[name][8],
           'resources':{'steel':2 if name in armored|mechanized|motors else 1}}
        if name in {'transport_helo','attack_helo','uav'}:e['resources']={'aluminium':2,'rubber':1}
        if name in {'nyto','doll','basic_robot','aa02','doomsday_dog'}:e['resources']['aluminium']=1
        if name in {'atgm','missile'}:e['resources']['tungsten']=1
        pairs.append((ident,e))
        pairs.append((ident+'_1',{'year':2060,'archetype':ident,'priority':100,'visual_level':0,'is_buildable':'yes','active':'no'}))
    emit('common/units/equipment/APDC_land_equipment.txt',
         '# First-integration baselines; see tools/unit_overhaul/catalog.py. No tank-designer dependency.\nequipments = {\n'+render(pairs,1)+'}\n')

def main():
    units=[build_unit(u) for u in SOURCE['units']]
    sections={'combat':units[:49],'divisional_support':units[49:74],'regimental_support':units[74:]}
    for name,items in sections.items():
        emit('common/units/APDC_'+name+'.txt','sub_units = {\n'+''.join(u['text'] for u in items)+'}\n')
    equipments()
    regular=[u['id'] for u in units if u['index'] not in (16,17)]
    eqs=['apdc_'+k+'_equipment_1' for k in EQUIPMENT_NAMES]+['infantry_equipment_2','support_equipment_1','motorized_equipment_1']
    tech={'allow':{'always':'no'},'start_year':2060,'research_cost':1,
          'enable_subunits':regular,'enable_equipments':eqs,'ai_will_do':{'factor':0}}
    egg={'allow':{'always':'no'},'start_year':2060,'research_cost':1,
         'enable_subunits':[UNIT_IDS[15],UNIT_IDS[16]],'ai_will_do':{'factor':0}}
    emit('common/technologies/APDC_land_units.txt','technologies = {\n'+render({'APDC_land_units_bootstrap':tech,'APDC_land_units_easter_eggs':egg},1)+'}\n')
    emit('common/on_actions/APDC_land_units.txt','''on_actions = {
    on_startup = { effect = { every_country = { APDC_initialize_land_units = yes } } }
    on_monthly = { effect = { every_country = { APDC_initialize_land_units = yes } } }
}
''')
    emit('common/scripted_effects/APDC_land_units.txt','''APDC_initialize_land_units = {
    if = {
        limit = { NOT = { has_tech = APDC_land_units_bootstrap } }
        set_technology = { APDC_land_units_bootstrap = 1 popup = no }
        log = "APDC_LAND_UNITS bootstrap [THIS.GetTag]"
    }
    if = {
        limit = { NOT = { has_country_flag = APDC_basic_template_initialized } }
        if = {
            limit = { NOT = { tag = MAD } }
            load_oob = APDC_basic_template
        }
        set_country_flag = APDC_basic_template_initialized
    }
}
''')
    tag_files={}
    for root in (Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV'),ROOT):
        for p in (root/'common/unit_tags').glob('*.txt'):
            if p.name!='APDC_categories.txt':tag_files[p.name]=p
    existing_cats={n.key for p in tag_files.values() for n in walk(parse(p.read_text('utf-8-sig'))) if n.op==''}
    cats=sorted(set(c for u in units for c in u['data']['categories'])-existing_cats)
    emit('common/unit_tags/APDC_categories.txt','sub_unit_categories = { '+' '.join(cats)+' }\n')
    loc={}
    for u in units:
        loc[u['id']]=u['name']; loc[u['id']+'_desc']=u['name']+'。按项目营级单位方案列装。'
    for key,name in EQUIPMENT_NAMES.items():
        k='apdc_'+key+'_equipment'
        for x in (k,k+'_1',k+'_short',k+'_1_short'):loc[x]=name
        for x in (k+'_desc',k+'_1_desc'):loc[x]=name+'。首版装备基准，生产和战斗数值仍需平衡验收。'
    loc.update({'APDC_land_units_bootstrap':'APDC常规陆军列装','APDC_land_units_easter_eggs':'APDC彩蛋列装',
        'category_apdc_units':'APDC陆军单位','category_apdc_dolls':'自律战术人形',
        'category_apdc_robots':'自律机械','category_apdc_elite_mechanical':'精锐机械单位',
        'combat_support':'自动化营组', 'APDC_units_testing':'APDC列装测试',
        'APDC_units_test_regular':'领取列装测试装备与训练编制','APDC_units_test_eggs':'解锁柳芭老妈与UMP姐妹（彩蛋）'})
    for language in ('simp_chinese','english'):
        emit(f'localisation/{language}/replace/zz_APDC_land_units_l_{language}.yml',f'l_{language}:\n'+''.join(f' {k}:0 "{v}"\n' for k,v in loc.items()),True)
    # Optional test decisions are human-only and NEVER grant equipment without an explicit click.
    emit('common/decisions/categories/APDC_units_testing.txt','''APDC_units_testing = {
    icon = generic_prepare_civil_war
    allowed = { always = yes }
    visible = { is_ai = no }
}
''')
    emit('common/decisions/APDC_units_testing.txt','''APDC_units_testing = {
    APDC_units_test_regular = {
        icon = generic_army_support
        visible = { is_ai = no }
        available = { always = yes }
        cost = 0
        fire_only_once = yes
        complete_effect = { country_event = { id = APDC_UNITS.1 } }
        ai_will_do = { factor = 0 }
    }
    APDC_units_test_eggs = {
        icon = generic_army_support
        visible = { is_ai = no NOT = { has_tech = APDC_land_units_easter_eggs } }
        available = { always = yes }
        cost = 0
        fire_only_once = yes
        complete_effect = { set_technology = { APDC_land_units_easter_eggs = 1 popup = no } }
        ai_will_do = { factor = 0 }
    }
}
''')
    effects=[('set_technology',{'APDC_land_units_bootstrap':1,'popup':'no'}),('army_experience',500)]
    for e in eqs:effects.append(('add_equipment_to_stockpile',{'type':e,'amount':3000,'producer':'ROOT'}))
    effects.append(('load_oob','APDC_unit_test_templates'))
    emit('events/APDC_unit_testing.txt','add_namespace = APDC_UNITS\ncountry_event = {\n id = APDC_UNITS.1\n hidden = yes\n is_triggered_only = yes\n immediate = {\n'+render(effects,2)+' }\n}\n')
    templates=[]
    for u in units:
        if u['index'] in (16,17):continue
        # Verification fixtures only. No manpower/divisions are spawned and no design-document divisions are implemented.
        body={'name':'"列装测试 '+u['name']+'"','regiments':{u['id'] if u['index']<=49 else UNIT_IDS[1]:{'x':0,'y':0}}}
        if 50<=u['index']<=74:body['support']={u['id']:{'x':0,'y':0}}
        if u['index']>=75:
            group=u['data']['allowed_battalion_groups'][0]
            lead={'infantry':2,'mobile':3,'armor':18,'combat_support':26,'mobile_combat_support':44,'armor_combat_support':20}[group]
            # Engine requires three battalions in the same column before a
            # regimental support slot exists; a one-battalion fixture is stripped.
            body['regiments']='{ '+ ' '.join(UNIT_IDS[lead-1]+' = { x = 0 y = '+str(y)+' }' for y in range(3))+' }'
            body['regimental_support']={u['id']:{'x':0,'y':0}}
        templates.append(('division_template',body))
    emit('history/units/APDC_unit_test_templates.txt','# Optional per-type fixtures. Regimental supports require three line battalions in their column. No automatic start-game deployment.\n'+render(templates))
    (WORK/'normalized_units.json').write_text(json.dumps(units,ensure_ascii=False,indent=2),encoding='utf-8')
    (WORK/'normalization_notes.json').write_text(json.dumps(NOTES,ensure_ascii=False,indent=2),encoding='utf-8')
    for path in STAGE.rglob('*.txt'):parse(path.read_text('utf-8-sig'))
    print(json.dumps({'units':len(units),'combat':49,'divisional_support':25,'regimental_support':8,'new_equipment':len(EQUIPMENT_NAMES),'notes':NOTES},ensure_ascii=False))

if __name__=='__main__':main()
