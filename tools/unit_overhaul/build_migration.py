"""Prepare compatibility overlays and surgical reference migrations; originals stay intact."""
from pathlib import Path
import json,re
from cw import parse,walk,patches,render
from build_core import ROOT,WORK,STAGE,emit
from catalog import LEGACY_MAP,UNIT_IDS,EQUIPMENT_ALIASES

GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
LAND_GROUPS={'infantry','mobile','armor','combat_support','mobile_combat_support','armor_combat_support','support'}

def original(rel):
    backup=WORK/'backup/files'/rel
    if backup.is_file():return backup
    manifest=WORK/'backup/manifest.json'
    if manifest.exists():
        record=json.loads(manifest.read_text('utf8')).get(Path(rel).as_posix())
        if record and not record['existed_before'] and (GAME/rel).is_file():return GAME/rel
    return ROOT/rel if (ROOT/rel).is_file() else GAME/rel

def effective(directory):
    names={p.relative_to(GAME) for p in (GAME/directory).rglob('*.txt')}
    names.update(p.relative_to(ROOT) for p in (ROOT/directory).rglob('*.txt') if not p.name.startswith('APDC_'))
    return [(rel,original(rel)) for rel in sorted(names)]

def main():
    disabled=set(); report=[]; legacy_map=dict(LEGACY_MAP)
    equipment_bonus_map={
        'mechanized_equipment':['tracked_mech','wheeled_mech','airborne_ifv'],
        'amphibious_mechanized_equipment':['amphib_mech'],
        'armored_car_equipment':['wheeled_mech'],
        'transport_helicopter_equipment':['transport_helo'], 'helicopter_equipment':['transport_helo'],
        'helicopter_gunship_equipment':['attack_helo'],
        'modern_tank_chassis':['mbt','tank_support'], 'modern_tank_equipment':['mbt','tank_support'],
        'light_tank_chassis':['light_tank','airborne_tank'], 'light_tank_equipment':['light_tank','airborne_tank'],
        'amphibious_tank_chassis':['amphib_tank'], 'amphibious_tank_equipment':['amphib_tank'],
        'modern_tank_artillery_chassis':['spg'], 'modern_tank_artillery_equipment':['spg'],
        'modern_tank_aa_chassis':['spaag'], 'modern_tank_aa_equipment':['spaag'],
        'modern_tank_destroyer_chassis':['atgm'], 'modern_tank_destroyer_equipment':['atgm'],
        'anti_air_equipment':['spaag'], 'anti_tank_equipment':['atgm'],
        'artillery_equipment':['towed_gun','truck_art','multipod_art','mortar'],
        'motorized_rocket_equipment':['mlrs'], 'rocket_artillery_equipment':['mlrs'],
        'armored_support_vehicle':['engineer_vehicle'],
    }
    # File-level overlays preserve naval/air/HQ entries and keep old land IDs resolvable.
    rels={p.relative_to(GAME) for p in (GAME/'common/units').glob('*.txt')}
    rels.update(p.relative_to(ROOT) for p in (ROOT/'common/units').glob('*.txt') if not p.name.startswith('APDC_'))
    for rel in sorted(rels):
        path=original(rel);text=path.read_text('utf-8-sig');roots=parse(text);edits=[]
        base=GAME/rel
        if base.is_file() and path!=base:
            base_roots=parse(base.read_text('utf-8-sig'))
            current_root=next((n for n in roots if n.key=='sub_units'),None)
            if current_root:
                known={u.key for u in current_root.children};missing=[]
                base_text=base.read_text('utf-8-sig')
                for b in base_roots:
                    if b.key!='sub_units':continue
                    for u in b.children:
                        if u.key not in known and u.val('group') in LAND_GROUPS:
                            missing.append(base_text[u.start:u.end])
                if missing:
                    text=patches(text,[(current_root.end-1,current_root.end-1,'\n# Restored inactive legacy IDs required by inherited scripts.\n'+'\n'.join(missing)+'\n')])
                    roots=parse(text)
        for root in roots:
            if root.key!='sub_units':continue
            for u in root.children:
                if u.val('group') not in LAND_GROUPS or u.val('allow_in_non_army_hq')=='no':continue
                disabled.add(u.key)
                if u.key not in legacy_map:
                    if 'sp_anti_air' in u.key:legacy_map[u.key]=UNIT_IDS[76 if 'support' in u.key else 20]
                    elif 'tank_destroyer' in u.key:legacy_map[u.key]=UNIT_IDS[77 if 'support' in u.key else 19]
                    elif 'sp_artillery' in u.key:legacy_map[u.key]=UNIT_IDS[78 if 'support' in u.key else 45]
                a=u.get('active')
                if a:edits.append((a.value_start,a.value_end,'no'))
                else:edits.append((u.value_start+1,u.value_start+1,'\n\t\tactive = no # legacy compatibility only\n'))
                invalid_equipment={'helicopter_equipment':'apdc_transport_helo_equipment',
                                   'helicopter_gunship':'apdc_attack_helo_equipment',
                                   'motorbike_equipment':'motorized_equipment'}
                for n in walk(u.children):
                    if n.key in invalid_equipment:
                        edits.append((n.start,n.start+len(n.key),invalid_equipment[n.key]))
                    elif n.key=='transport' and n.value in invalid_equipment:
                        edits.append((n.value_start,n.value_end,invalid_equipment[n.value]))
        if edits:
            emit(rel,'# APDC: old land-unit IDs retained for reference compatibility; normal unlocks removed.\n'+patches(text,edits))
            report.append({'path':rel.as_posix(),'kind':'disable_legacy_units','changes':len(edits)})
    # Mirror bonuses onto new IDs without unlocking old battalions. File overlays are
    # limited to the technology and doctrine sources that actually need migration.
    for folder in ('common/technologies','common/doctrines','common/special_projects/projects'):
        for rel,path in effective(folder):
            text=path.read_text('utf-8-sig')
            if 'enable_subunits' not in text and not any(re.search(r'\b'+re.escape(k)+r'\s*=',text) for k in list(legacy_map)+list(equipment_bonus_map)):continue
            try:roots=parse(text)
            except Exception as ex:raise RuntimeError(f'Cannot safely migrate {path}: {ex}')
            edits=[]
            def visit(nodes):
                for n in nodes:
                    if n.key=='enable_subunits':
                        kept=[x.value for x in n.children if x.value not in disabled]
                        if len(kept)!=len(n.children):
                            if kept:edits.append((n.value_start,n.value_end,'{ '+' '.join(kept)+' }'))
                            else:edits.append((n.start,n.end,'# APDC: retired land-unit unlock removed.'))
                        continue
                    visit(n.children)
                # Duplicate aliases only once within the same scope. Keep legacy data,
                # so old focuses/technologies remain loadable rather than dangling.
                added=set(n.key for n in nodes)
                for n in nodes:
                    if (n.key in legacy_map or n.key in equipment_bonus_map) and n.children:
                        targets=([legacy_map[n.key]] if n.key in legacy_map else [])+['apdc_'+k+'_equipment' for k in equipment_bonus_map.get(n.key,[])]
                        additions=[]
                        for target in targets:
                            if target in added:continue
                            body=text[n.start:n.end]
                            # Clone original numeric modifier blocks only, never nested unit definitions or conditions.
                            if all(x.value is not None and re.fullmatch(r'[+-]?[\d.]+',x.value) for x in n.children):
                                additions.append('\n\t\t'+target+body[len(n.key):])
                                added.add(target)
                        if additions:edits.append((n.end,n.end,''.join(additions)))
            visit(roots)
            if edits:
                emit(rel,patches(text,edits));report.append({'path':rel.as_posix(),'kind':'technology_doctrine_references','changes':len(edits)})
    # Existing starting divisions retain their composition and location, only their
    # battalion IDs change. No document appendix division layouts are used.
    for path in (ROOT/'history/units').glob('*.txt'):
        if path.name=='APDC_unit_test_templates.txt':continue
        rel=path.relative_to(ROOT);text=original(rel).read_text('utf-8-sig');edits=[]
        for n in walk(parse(text)):
            if n.key in legacy_map and n.children and n.get('x'):
                edits.append((n.start,n.start+len(n.key),legacy_map[n.key]))
        if edits:
            emit(rel,patches(text,edits));report.append({'path':rel.as_posix(),'kind':'existing_oob_unit_ids','changes':len(edits)})
    empty_rel=Path('history/units/APDC_empty.txt')
    original_empty=original(empty_rel).read_text('utf-8-sig')
    # Preserve the blank initialization OOB. Load the separate editing seed once
    # via APDC_initialize_land_units, so reloading APDC_empty cannot duplicate it.
    start_template='''
# APDC first-integration editing seed. No divisions or equipment are granted.
division_template = {
 name = "六营步兵师"
 regiments = {
  apdc_infantry = { x = 0 y = 0 }
  apdc_infantry = { x = 0 y = 1 }
  apdc_infantry = { x = 0 y = 2 }
  apdc_infantry = { x = 1 y = 0 }
  apdc_infantry = { x = 1 y = 1 }
  apdc_infantry = { x = 1 y = 2 }
 }
}
'''
    emit(empty_rel,original_empty)
    emit('history/units/APDC_basic_template.txt',start_template)
    for path in (ROOT/'history/countries').glob('*.txt'):
        rel=path.relative_to(ROOT);text=original(rel).read_text('utf-8-sig')
        if 'APDC_land_units_bootstrap' not in text:
            emit(rel,'# APDC: regular roster and production models available at scenario initialization.\nset_technology = { APDC_land_units_bootstrap = 1 }\n'+text)
            report.append({'path':rel.as_posix(),'kind':'country_start_unlock','changes':1})
    # Minimal safe AI baseline, independent of the later national division-design project.
    ai=[]
    ai_roles=[('infantry',{'apdc_infantry':6},{'apdc_engineer':1},80),
              ('motorized',{'apdc_motorized':6},{'apdc_combined_service':1},10),
              ('armor',{'apdc_light_tank':3,'apdc_motorized':6},{'apdc_engineer':1},5),
              ('apdc_automation',{'apdc_doll_small':6},{'apdc_robot_recon':1},5)]
    strategies=[]
    for role,reg,support,ratio in ai_roles:
        ai.append(('APDC_'+role+'_template',{'blocked_for':['AAA'], 'role':role,'upgrade_prio':{'factor':1},
            'APDC_'+role+'_baseline':{'upgrade_prio':{'factor':1},'target_template':{'regiments':reg,'support':support}}}))
        strategies.append(('ai_strategy',{'type':'role_ratio','id':role,'value':ratio}))
    emit('common/ai_templates/APDC_land_templates.txt','# Temporary AI migration baselines, not the design-document division appendix.\n'+render(ai))
    emit('common/ai_strategy/APDC_land_roles.txt','APDC_land_roles = {\n enable = { always = yes }\n abort_when_not_enabled = yes\n'+render(strategies,1)+'}\n')
    enum_rel=Path('common/script_enums.txt')
    enum_text=original(enum_rel).read_text('utf-8-sig')
    enum=next(n for n in parse(enum_text) if n.key=='script_enum_equipment_bonus_type')
    from catalog import EQUIPMENT_NAMES
    tokens=[f'apdc_{key}_equipment{suffix}' for key in EQUIPMENT_NAMES for suffix in ('','_1')]
    emit(enum_rel,patches(enum_text,[(enum.value_end-1,enum.value_end-1,'\n\t# APDC fixed-design equipment types\n\t'+'\n\t'.join(tokens)+'\n')]))
    (WORK/'legacy_unit_mapping.json').write_text(json.dumps(legacy_map,indent=2),'utf8')
    (WORK/'disabled_legacy_units.json').write_text(json.dumps(sorted(disabled),indent=2),'utf8')
    (WORK/'migration_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({'legacy_land_units_disabled':len(disabled),'migration_files':len(report),'country_start_unlocks':sum(r['kind']=='country_start_unlock' for r in report)},ensure_ascii=False))

if __name__=='__main__':main()
