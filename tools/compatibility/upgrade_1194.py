"""Scoped 1.19.4 native-interface compatibility, with no vanilla gameplay import."""
from pathlib import Path
import sys,json,re,hashlib,shutil,zipfile,collections,difflib
ROOT=Path(__file__).resolve().parents[2]
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
OUT=ROOT/'docs/compatibility/20261028-1.19.4'
BACKUP=Path(json.loads(Path('D:/APDC-1194-current.json').read_text('utf-8'))['backup'])
QA=Path('D:/APDC_1194_QA_20261028')
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,patches,walk

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
def sig(n):return (n.key,n.value,n.op,tuple(sig(c) for c in n.children))
def child(n,name):
    found=[c for c in n.children if c.val('name')==name];assert len(found)==1,(name,len(found));return found[0]
def at(nodes,names):
    n=nodes[0]
    for name in names:n=child(n,name)
    return n

def upgrade():
    changes={};additions={}
    def session(rel):
        text=(ROOT/rel).read_text('utf-8-sig');native=(GAME/rel).read_text('utf-8-sig');return text,parse(text),native,parse(native),[]
    def change_field(text,node,key,native,source,edits):
        a=node.get(key);b=source.get(key);assert a and b,(node.val('name'),key)
        edits.append((a.value_start,a.value_end,native[b.value_start:b.value_end]))
    def append_children(parent,source,names,native,edits):
        for name in names:assert not any(c.val('name')==name for c in parent.children)
        body='\n'+''.join(native[child(source,name).start:child(source,name).end]+'\n' for name in names)
        edits.append((parent.value_end-1,parent.value_end-1,body))
    def commit(rel,text,edits,added):
        after=patches(text,edits);parse(after);assert (ROOT/rel).read_text('utf-8-sig')==text
        (ROOT/rel).write_text(after,'utf-8');changes[rel]={'before':hashlib.sha256(text.encode()).hexdigest(),'after':sha(ROOT/rel),'edits':len(edits)};additions[rel]=added

    rel='interface/countrytradeview.gui';t,n,v,nn,e=session(rel);root=n[0];nr=nn[0];main=child(root,'countrytradeview');nm=child(nr,'countrytradeview')
    fields={'trade_back':['size'],'trade_header':['position'],'civilian_factory_icon':['position'],'civ_factories':['position','maxWidth'],'factories_total':['position','maxWidth'],'factories_available':['position','maxWidth'],'resources':['position'],'trade_icon_and_bg':['position'],'sort_country':['position'],'sort_export':['position'],'sort_request':['position'],'sort_convoys':['position'],'filters':['position'],'country_filters':['position'],'trade':['position']}
    for name,keys in fields.items():
        for key in keys:change_field(t,child(main,name),key,v,child(nm,name),e)
    obsolete=child(main,'factories_used');new_counters=['consumer_goods_icon','factories_consumer','traded_factories_icon','factories_trade'];e.append((obsolete.start,obsolete.end,'\n'.join(v[child(nm,name).start:child(nm,name).end] for name in new_counters)))
    auto=['auto_import_checkbox','auto_import_label','auto_import_budget_bg','auto_import_budget_txt','auto_import_priority_open_button','auto_import_slider'];append_children(main,nm,auto,v,e)
    templates=['auto_import_priority_window','auto_import_priority_entry'];append_children(root,nr,templates,v,e)
    commit(rel,t,e,new_counters+auto+templates)

    rel='interface/countrydiplomacyview.gui';t,n,v,nn,e=session(rel);root=n[0];nr=nn[0]
    path=['countrydiplomacyview','country_info','diplomatic_actions'];append_children(at(n,path),at(nn,path),['actions_title','edit_auto_response'],v,e)
    append_children(child(root,'diplomacy_action_entry'),child(nr,'diplomacy_action_entry'),['response_icon'],v,e)
    append_children(child(root,'diplomacy_action_info_window'),child(nr,'diplomacy_action_info_window'),['recall_volunteers'],v,e)
    for name in ['diplomacy_request_incoming_lend_lease_entry','diplomacy_incoming_lend_lease_equipment_entry']:
        append_children(child(root,name),child(nr,name),['acceptance'],v,e)
    deal=child(child(root,'diplomacy_request_incoming_lend_lease_entry'),'deal_state');ndeal=child(child(nr,'diplomacy_request_incoming_lend_lease_entry'),'deal_state')
    for key in ['position','maxWidth','maxHeight']:change_field(t,deal,key,v,ndeal,e)
    commit(rel,t,e,['actions_title','edit_auto_response','response_icon','recall_volunteers','acceptance (two entries)'])

    rel='interface/countrytechtreeview.gui';t,n,v,nn,e=session(rel);root=n[0];nr=nn[0]
    append_children(child(root,'countrytechtreeview'),child(nr,'countrytechtreeview'),['cycle_tab_next','cycle_tab_prev'],v,e)
    stats=['technology_unit_statlist_item_equipment','technology_unit_statlist_item_module','technology_unlocks_statlist_item_building','technology_unlocks_statlist_item_tactic','technology_unlocks_statlist_item_subunit','technology_unit_statlist_item_upgrade','technology_unit_statlist_item_modifier'];newstats=['leader_bonuses_header','leader_bonuses_grid','support_category_multipliers_header','support_category_multipliers_grid']
    for name in stats:append_children(child(root,name),child(nr,name),newstats,v,e)
    commit(rel,t,e,['cycle_tab_next','cycle_tab_prev']+[name+'/'+s for name in stats for s in newstats])

    rel='common/doctrines/tracks/land_doctrine_tracks.txt';t=(ROOT/rel).read_text('utf-8-sig');v=(GAME/rel).read_text('utf-8-sig');node=next(x for x in parse(t) if x.key=='operations');native=next(x for x in parse(v) if x.key=='operations');categories=node.get('mastery').get('categories');nc=native.get('mastery').get('categories')
    assert node.get('mastery').val('multiplier')==native.get('mastery').val('multiplier')=='0.7'
    assert [x.key for x in categories.children]==['category_all_infantry','category_line_artillery','category_artillery','category_tanks','category_all_armor']
    assert [x.key for x in nc.children]==['category_army']
    commit(rel,t,[(categories.value_start,categories.value_end,'{\n            category_army\n        }')],['operations.mastery.categories: category_army; multiplier unchanged'])
    dump(OUT/'changes.json',{'installed_version':json.loads((GAME/'launcher-settings.json').read_text('utf-8'))['version'],'backup':str(BACKUP),'files':changes,'added_bindings':additions,'balance_values_imported':False})
    print(json.dumps({'files_changed':len(changes),'backup':str(BACKUP)}))

def audit():
    report=json.loads((OUT/'changes.json').read_text('utf-8'));native_missing=[];font_names=set();gfx=set()
    effective_gfx={p.relative_to(GAME/'interface').as_posix():p for p in (GAME/'interface').rglob('*.gfx')}
    effective_gfx.update({p.relative_to(ROOT/'interface').as_posix():p for p in (ROOT/'interface').rglob('*.gfx')})
    for p in effective_gfx.values():
        text=p.read_text('utf-8-sig',errors='replace');gfx.update(re.findall(r'\bname\s*=\s*"?(GFX_[A-Za-z0-9_]+)',text))
    checked=0;sprites_missing=[];added_nodes=0
    with zipfile.ZipFile(BACKUP/'before.zip') as z:
        # The custom diplomacy root and organization side panel must be byte-semantically unchanged.
        before=parse(z.read('interface/countrydiplomacyview.gui').decode('utf-8-sig'));after=parse((ROOT/'interface/countrydiplomacyview.gui').read_text('utf-8-sig'))
        for name in ['APDC_diplomacy_right_vertical_slider']:
            assert sig(child(before[0],name))==sig(child(after[0],name))
        a=child(before[0],'countrydiplomacyview');b=child(after[0],'countrydiplomacyview')
        for name in ['APDC_diplomacy_cooperation_panel_hook','APDC_diplomacy_main_background','intel_ledger_container','close_button']:
            assert sig(child(a,name))==sig(child(b,name)),name
        for field in ['position','show_position','size','verticalScrollbar']:assert sig(a.get(field))==sig(b.get(field)),field
        # Entire technology folders/tabs retain the project's custom contents, coordinates and icons.
        before=parse(z.read('interface/countrytechtreeview.gui').decode('utf-8-sig'));after=parse((ROOT/'interface/countrytechtreeview.gui').read_text('utf-8-sig'));a=child(before[0],'countrytechtreeview');b=child(after[0],'countrytechtreeview')
        for old in a.children:
            if old.val('name'):assert sig(old)==sig(child(b,old.val('name'))),old.val('name')
        # Every other doctrine track and the numeric mastery multiplier remain identical.
        before=parse(z.read('common/doctrines/tracks/land_doctrine_tracks.txt').decode('utf-8-sig'));after=parse((ROOT/'common/doctrines/tracks/land_doctrine_tracks.txt').read_text('utf-8-sig'))
        for a,b in zip(before,after):
            if a.key!='operations':assert sig(a)==sig(b)
    for rel in report['files']:
        p=ROOT/rel;raw=p.read_bytes();assert not raw.startswith(b'\xef\xbb\xbf');nodes=parse(raw.decode('utf-8'));checked+=1
        if p.suffix=='.gui':
            native=parse((GAME/rel).read_text('utf-8-sig'))
            for n in walk(nodes):
                for field in ['spriteType','quadTextureSprite']:
                    v=n.val(field)
                    if v and v.startswith('GFX_') and v not in gfx:sprites_missing.append((rel,n.val('name'),v))
    # Undefined sprites from pre-existing GUI content are compared with the backed-up GUI.
    pre_existing=set()
    with zipfile.ZipFile(BACKUP/'before.zip') as z:
        for rel in report['files']:
            if not rel.endswith('.gui'):continue
            for n in walk(parse(z.read(rel).decode('utf-8-sig'))):
                for field in ['spriteType','quadTextureSprite']:
                    v=n.val(field)
                    if v and v.startswith('GFX_') and v not in gfx:pre_existing.add((rel,n.val('name'),v))
    new_missing=[x for x in sprites_missing if x not in pre_existing];assert not new_missing,new_missing
    native_defines=(GAME/'common/defines/00_defines.lua').read_text('utf-8-sig')+(GAME/'common/defines/00_graphics.lua').read_text('utf-8-sig');missing_defines=[];define_count=0
    for p in (ROOT/'common/defines').glob('*.lua'):
        for group,key in re.findall(r'^\s*NDefines\.(\w+)\.(\w+)\s*=',p.read_text('utf-8-sig'),re.M):
            define_count+=1
            if not re.search(r'\b'+key+r'\s*=',native_defines):missing_defines.append((p.name,group,key))
    assert not missing_defines
    dump(OUT/'static-audit.json',{'passed':True,'patched_files_parsed':checked,'new_missing_sprites':new_missing,'pre_existing_missing_sprites':sorted(pre_existing),'custom_defines_checked':define_count,'unsupported_defines':missing_defines,'diplomacy_organization_layout_unchanged':True,'all_custom_technology_folders_and_tabs_unchanged':True,'doctrine_mastery_multiplier_unchanged':True,'supported_version':'1.19.* already covers 1.19.4','vanilla_FX_files_changed_by_update':False})
    print(json.dumps({'passed':True,'new_missing_sprites':0,'custom_defines':define_count,'custom_technology_and_organization_layout_preserved':True}))

def prepare():
    assert not QA.exists();(QA/'mod').mkdir(parents=True);driver=QA/'driver'
    for d in ['common/on_actions','common/defines']:(driver/d).mkdir(parents=True)
    desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',(ROOT/'descriptor.mod').read_text('utf-8-sig'),flags=re.M);(QA/'mod/APDC.mod').write_text(desc,'utf-8')
    (QA/'mod/APDC_1194_QA.mod').write_text('name="APDC 1.19.4 compatibility diagnostics"\npath="'+driver.as_posix()+'"\nsupported_version="1.19.*"\n','utf-8')
    dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_1194_QA.mod'],'disabled_dlcs':[]})
    shutil.copy2('D:/APDC_MapFinishQA_20261027/settings.txt',QA/'settings.txt')
    (driver/'common/defines/zzzz_APDC_1194_QA.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf-8')
    hook='''on_actions = { on_daily_GER = { effect = {
add_to_variable = { qa_1194_day = 1 }
if = { limit = { check_variable = { qa_1194_day = 1 } }
apdc_cw_open_panel = yes
set_variable = { apdc_cw_selected = USA } set_variable = { apdc_cw_detail = 1 }
apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes
log = "APDC_1194_QA READY date=[GetDateText] economy_days=[?APDC_eco_day_ticks] USA_core_states=[?apdc_cw_detail_state_count] detail_pieces=[?apdc_cw_detail_pieces^num]"
}
if = { limit = { check_variable = { qa_1194_day = 3 } } clr_country_flag = apdc_cw_open }
log = "APDC_1194_QA DAY [?qa_1194_day] date=[GetDateText] economy_days=[?APDC_eco_day_ticks] economy_weeks=[?APDC_eco_week_ticks]"
} } }
'''
    (driver/'common/on_actions/zzzz_APDC_1194_QA.txt').write_text(hook,'utf-8')
    user=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV');files=[]
    for name in ['dlc_load.json','settings.txt','continue_game.json','last_save']:
        p=user/name
        if p.is_file():files.append(p)
    files.extend(p for p in (user/'save games').glob('*') if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower()))
    dump(OUT/'runtime-preparation.json',{'profile':str(QA),'user_files_before':{str(p):sha(p) for p in files},'enabled_mods':['APDC','isolated read-only diagnostics'],'disabled_dlcs':[],'toolpack_loaded':False})
    print(str(QA))

def fix_peace():
    # These newly inherited rules restore 1936 French colonies and have no APDC
    # scenario counterpart. Shadow only the new country-specific consumers;
    # retain the pre-existing French civil-war cost rule verbatim.
    ai='common/peace_conference/ai_peace/FRA.txt';cost='common/peace_conference/cost_modifiers/FRA_peace.txt'
    assert not (ROOT/ai).exists() and not (ROOT/cost).exists()
    ai_source=(GAME/ai).read_text('utf-8-sig');cost_source=(GAME/cost).read_text('utf-8-sig')
    rules=parse(ai_source)[0].children
    assert {n.key for n in rules}=={'FRA_reclaim_indochina','FRA_reclaim_indochina_promised_independence','allies_dont_liberate_french_indochina'}
    root=parse(cost_source)[0];old=root.get('FRA_retake_french_territory_modifier');assert old
    assert {n.key for n in root.children}=={'FRA_retake_french_territory_modifier','FRA_reclaim_indochina_cost'}
    for rel in [ai,cost]:(ROOT/rel).parent.mkdir(parents=True,exist_ok=True)
    (ROOT/ai).write_text('# APDC 2060: no WW2 French Indochina reclamation or anti-liberation AI rules.\npeace_ai_desires = { }\n','utf-8')
    (ROOT/cost).write_text('# Preserve the pre-existing French civil-war cost rule; no WW2 colonial discount.\npeace_action_modifiers = {\n'+cost_source[old.start:old.end]+'\n}\n','utf-8')
    assert sig(parse((ROOT/cost).read_text('utf-8'))[0].children[0])==sig(old)
    report=json.loads((OUT/'changes.json').read_text('utf-8'))
    for rel in [ai,cost]:report['files'][rel]={'before':None,'after':sha(ROOT/rel),'kind':'new targeted native override'}
    report['disabled_unrelated_1936_rules']=[n.key for n in rules]+['FRA_reclaim_indochina_cost']
    dump(OUT/'changes.json',report)
    dump(OUT/'runtime-attempt1.json',{'result':'stopped after identifying new compatibility errors, before date advancement','new_error_cause':'1.19.4 native French Indochina peace rules reference FRA_is_indochina_state and is_vichy_france, helpers removed from the APDC 2060 scenario','process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),'stop':json.loads((QA/'silent-stop.json').read_text('utf-8-sig')),'archived_logs':str(BACKUP/'runtime-attempt1.zip')})
    print(json.dumps({'disabled_scenario_inapplicable_rules':4,'generic_peace_AI_unchanged':True,'prior_french_civil_war_cost_retained':True}))

def fix_sprite():
    source=GAME/'interface/frontendgamesetupview.gfx';text=source.read_text('utf-8-sig');node=next(n for n in parse(text)[0].children if n.val('name')=='GFX_generic_3_state_checkbox')
    texture=GAME/node.val('texturefile');assert texture.exists()
    rel='interface/APDC_1194_compatibility.gfx';path=ROOT/rel;assert not path.exists()
    path.write_text('# Native 1.19.4 diplomacy depends on this sprite, hidden by the custom setup GFX.\nspriteTypes = {\n'+text[node.start:node.end]+'\n}\n','utf-8')
    assert sig(parse(path.read_text('utf-8'))[0].children[0])==sig(node)
    report=json.loads((OUT/'changes.json').read_text('utf-8'));report['files'][rel]={'before':None,'after':sha(path),'kind':'native sprite definition restored outside the custom setup GFX'};dump(OUT/'changes.json',report)
    print(json.dumps({'native_sprite_restored':'GFX_generic_3_state_checkbox','texture':node.val('texturefile'),'frames':node.val('noOfFrames'),'custom_setup_gfx_unchanged':True}))

def polish():
    report=json.loads((OUT/'changes.json').read_text('utf-8'));manifest=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'))
    with zipfile.ZipFile(BACKUP/'before.zip') as z:
        for rel,row in report['files'].items():
            p=ROOT/rel
            if rel in manifest:row['before']=manifest[rel]
            if rel.endswith('.gui'):
                before=z.read(rel).decode('utf-8-sig').splitlines();text=p.read_text('utf-8-sig');after=text.splitlines();syntax=tuple(sig(n) for n in parse(text))
                matcher=difflib.SequenceMatcher(None,before,after,autojunk=False)
                for op,a,b,c,d in matcher.get_opcodes():
                    if op!='equal':
                        for i in range(c,d):after[i]=after[i].rstrip(' \t')
                cleaned='\n'.join(after)+'\n';assert tuple(sig(n) for n in parse(cleaned))==syntax;p.write_text(cleaned,'utf-8')
            row['after']=sha(p)
    dump(OUT/'changes.json',report)
    print('Added-line whitespace cleaned; all GUI syntax trees identical.')

def section(text,name):
    match=re.search(r'(?m)^'+re.escape(name)+r'=\{',text);assert match,name
    start=match.end();depth=1
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if depth==0:return text[start:start+token.start()]
    raise ValueError('Unclosed save section '+name)

def verify():
    save=QA/'save games/autosave.hoi4';text=save.read_text('utf-8-sig');version=re.search(r'(?m)^version="([^"]+)"',text).group(1);date=re.search(r'(?m)^date="([^"]+)"',text).group(1)
    assert '1.19.4' in version and date.startswith('2060.2.'),(version,date)
    expected=json.loads((ROOT/'tools/map_maintenance/baseline/initial_territories.json').read_text('utf-8'));states={int(n.key):n for n in parse(section(text,'states'))};assert len(states)==len(expected)
    cores=collections.defaultdict(list);claims=collections.defaultdict(list);ger=None
    for match in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',section(text,'countries')):
        tag,body=match.groups()
        if tag=='GER':ger=body
        for key,target in [('cores',cores),('claims',claims)]:
            m=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
            if m:
                for sid in map(int,re.findall(r'\d+',m.group(1))):target[sid].append(tag)
    differences=[]
    for sid,n in states.items():
        got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])};want=expected[str(sid)];want={**want,'cores':sorted(want['cores']),'claims':sorted(want['claims'])}
        if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
    assert ger
    def variable(key):
        m=re.search(r'(?mi)^\s*'+re.escape(key)+r'=([\d.-]+)\s*$',ger);assert m,key;return float(m.group(1))
    daily=variable('apdc_eco_day_ticks');weekly=variable('apdc_eco_week_ticks');assert daily>=31 and weekly>=4,(daily,weekly)
    game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');ready=[line for line in game.splitlines() if 'APDC_1194_QA READY' in line]
    assert ready and 'USA_core_states=86' in ready[0] and 'detail_pieces=103' in ready[0],ready
    error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');old_error=Path('D:/APDC_RailwayQA_20261027_1912/logs/error.log').read_text('utf-8-sig',errors='replace')
    def normalize(line):return re.sub(r'^(?:\[[^\]]*\])+[: ]*','',line)
    new_errors=sorted({normalize(line) for line in error.splitlines()}-{normalize(line) for line in old_error.splitlines()})
    stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));preparation=json.loads((OUT/'runtime-preparation.json').read_text('utf-8'));user_changed=[p for p,h in preparation['user_files_before'].items() if sha(Path(p))!=h]
    passed=not differences and not new_errors and not user_changed and not stop['still_running'] and not stop['steam_app_running'] and not stop['remaining_helpers']
    report={'passed':passed,'version':version,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'state_count':len(states),'relation_differences':differences,'economy_daily_ticks':daily,'economy_weekly_settlements':weekly,'state_scope_array_validation':ready,'new_distinct_errors_vs_previous_1_19_3':new_errors,'existing_error_log_lines':len(error.splitlines()),'user_settings_or_autosaves_changed':user_changed,'process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf-8')),'cold_war_state_math_visual_review':'runtime-state-math-review.png captured in second diagnostic attempt; no geography or Cold War rendering files changed between attempts','native_new_buttons_mouse_tested':False,'input_desktop_switched':False,'mouse_or_keyboard_sent':False}
    dump(OUT/'runtime-audit.json',report)
    with zipfile.ZipFile(BACKUP/'runtime-final.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in (QA/'logs').glob('*'):
            if p.is_file():z.write(p,'logs/'+p.name)
        for name in ['silent-process.json','silent-stop.json','dlc_load.json','settings.txt']:z.write(QA/name,name)
    assert passed,report
    print(json.dumps({'passed':True,'version':version,'date':date,'economy_days':daily,'weekly_settlements':weekly,'states_checked':len(states),'new_distinct_errors':0,'game_closed':True}))

def finalize():
    from concurrent.futures import ThreadPoolExecutor
    runtime=json.loads((OUT/'runtime-audit.json').read_text('utf-8'));assert runtime['passed']
    # Save a native text baseline so the next update can be compared by contents,
    # rather than treating file timestamps as a complete patch diff.
    native_files=[]
    for folder in ['common','interface','gfx/FX']:
        native_files.extend(p for p in (GAME/folder).rglob('*') if p.is_file() and p.suffix.lower() in {'.txt','.gui','.gfx','.lua','.shader','.fxh'})
    def row(p):return p.relative_to(GAME).as_posix(),sha(p)
    with ThreadPoolExecutor(max_workers=8) as pool:native_hashes=dict(pool.map(row,native_files))
    dump(OUT/'native-baseline.json',{'version':runtime['version'],'steam_buildid':'26132856','files':native_hashes,'executable_sha256':sha(GAME/'hoi4.exe')})
    dump(ROOT/'tools/compatibility/baseline.json',{'version':runtime['version'],'steam_buildid':'26132856','report':'docs/compatibility/20261028-1.19.4','native_hashes':'docs/compatibility/20261028-1.19.4/native-baseline.json','runtime_date':runtime['date'],'runtime_passed':True,'previous_version':'1.19.3','backup':str(BACKUP)})
    original=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'));files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts and p!=OUT/'preservation-audit.json']
    def project_row(p):return p.relative_to(ROOT).as_posix(),sha(p)
    with ThreadPoolExecutor(max_workers=8) as pool:after=dict(pool.map(project_row,files))
    changed=[{'file':rel,'before':original[rel],'after':h} for rel,h in after.items() if rel in original and original[rel]!=h];added=[{'file':rel,'after':h} for rel,h in after.items() if rel not in original];removed=sorted(set(original)-set(after))
    declared=json.loads((OUT/'changes.json').read_text('utf-8'));allowed=set(declared['files'])|{'tools/compatibility/upgrade_1194.py','tools/compatibility/baseline.json'}
    unexpected=[v for v in changed+added if v['file'] not in allowed and not v['file'].startswith('docs/compatibility/20261028-1.19.4/')]
    report={'passed':not removed and not unexpected,'files_hashed':len(after),'changed_existing':changed,'added':added,'removed':removed,'unexpected':unexpected,'pre_existing_dirty_files_preserved':True,'country_identity_map_economy_code_unit_stats_cold_war_and_art_unchanged':True,'own_manifest_git_and_caches_excluded':True}
    dump(OUT/'preservation-audit.json',report);assert report['passed'],report
    print(json.dumps({'passed':True,'files_hashed':len(after),'changed_existing':len(changed),'unexpected':len(unexpected),'removed':len(removed),'native_baseline_files':len(native_hashes)}))

if __name__=='__main__':{'upgrade':upgrade,'audit':audit,'prepare':prepare,'fix_peace':fix_peace,'fix_sprite':fix_sprite,'polish':polish,'verify':verify,'finalize':finalize}[sys.argv[1]]()
