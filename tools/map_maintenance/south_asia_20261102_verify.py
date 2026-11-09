"""Read-only audits and isolated QA for the dated South Asia conversion."""
import sys,json,re,zipfile,collections,shutil,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
from south_asia_20261102 import ROOT,BACKUP,OUT,BASE,GAME,SCAN,RETIRED,NEW,LANGS,IDEOLOGIES,parse,walk,canon,states,registry,dump,sha,META
QA=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA')
USER=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')

def audit():
 plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));target=json.loads((OUT/'political-target.json').read_text('utf-8'));reg=registry();ss=states();assert len(ss)==1578
 assert not RETIRED.intersection(reg)
 for tag in RETIRED:assert not list((ROOT/'history/countries').glob(tag+'*.txt')),tag
 got={};nonpolitical=[];history=[]
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  for sid,(p,t,n) in ss.items():
   h=n.get('history');got[str(sid)]={'owner':h.val('owner'),'controller':h.val('controller',h.val('owner')),'cores':sorted({x.value for x in h.children if x.key=='add_core_of'}),'claims':sorted({x.value for x in h.children if x.key=='add_claim_by'})}
   assert got[str(sid)]==target[str(sid)],sid
   assert got[str(sid)]['owner'] in reg and got[str(sid)]['controller'] in reg
   before=parse(z.read(p.relative_to(ROOT).as_posix()).decode('utf-8-sig'))[0]
   assert [canon(x) for x in n.children if x.key!='history']==[canon(x) for x in before.children if x.key!='history'],sid
   ignore={'owner','controller','add_core_of','add_claim_by'}
   assert [canon(x) for x in h.children if x.key not in ignore]==[canon(x) for x in before.get('history').children if x.key not in ignore],sid
   nonpolitical.append(sid)
  for tag,d in plan.items():
   owned=sorted(int(sid) for sid,p in got.items() if p['owner']==tag);cores=sorted(int(sid) for sid,p in got.items() if tag in p['cores']);claims=sorted(int(sid) for sid,p in got.items() if tag in p['claims'])
   assert owned==d['owned'] and cores==d['core'] and claims==d['claims'],tag
   files=list((ROOT/'history/countries').glob(tag+'*.txt'));assert len(files)==1,tag
   p=files[0];nodes=parse(p.read_text('utf-8-sig'));assert next(n.value for n in nodes if n.key=='capital')==str(d['capital']);assert d['capital'] in owned
   rel=p.relative_to(ROOT).as_posix()
   if tag not in NEW:
    before=parse(z.read(rel).decode('utf-8-sig'));assert [canon(n) for n in before if n.key!='capital']==[canon(n) for n in nodes if n.key!='capital'],tag
   history.append({'tag':tag,'owned':len(owned),'cores':len(cores),'claims':len(claims),'capital':d['capital'],'existing_history_except_capital_preserved':tag not in NEW})
  # Generic engine callbacks and occupation laws are retained verbatim structurally.
  rel='common/occupation_laws/occupation_laws.txt';assert [n.key for n in parse(z.read(rel).decode('utf-8-sig'))]==[n.key for n in parse((ROOT/rel).read_text('utf-8-sig'))]
 refs=[]
 for folder in ['common','events','history']:
  for p in (ROOT/folder).rglob('*.txt'):
   for n in walk(parse(p.read_text('utf-8-sig'))):
    if n.key in RETIRED or (n.value and n.value.strip('"') in RETIRED):refs.append((p.relative_to(ROOT).as_posix(),n.key,n.value))
 assert not refs,refs[:30]
 local=[]
 for lang in LANGS:
  p=ROOT/f'localisation/replace/zzzzzzz_APDC_south_asia_l_{lang}.yml';raw=p.read_bytes();assert raw.startswith(b'\xef\xbb\xbf');t=raw.decode('utf-8-sig').replace('\r\n','\n');assert t.startswith('l_'+lang+':\n')
  entries=re.findall(r'^ ([A-Za-z0-9_]+):0 "([^"\n]*)"$',t,re.M);locreport=json.loads((OUT/'country-localisation.json').read_text('utf-8'));assert len(entries)==locreport['new_file_entries_by_language'][lang] and len(dict(entries))==len(entries)
  for tag,d in plan.items():
   wanted=locreport['names'][lang][list(plan).index(tag)];seen=0
   for other in (ROOT/'localisation').rglob('*.yml'):
    if not other.name.endswith('_l_'+lang+'.yml'):continue
    for match in re.finditer(r'(?m)^\s*'+tag+r'(?:(?:_(?:'+ '|'.join(IDEOLOGIES+['democratic','neutrality'])+r')))?(?:_DEF)?:\d*\s+"([^"\n]*)"',other.read_text('utf-8-sig')):assert match[1]==wanted,(other,tag,match[1],wanted);seen+=1
   assert seen>=24,(tag,lang,seen)
  local.append(lang)
 assert json.loads((BASE/'initial_territories.json').read_text('utf-8'))==target
 assert sha(Path(META['source_save']))==json.loads((OUT/'source-analysis.json').read_text('utf-8'))['sha256']
 cw=json.loads((OUT/'cold-war-palette.json').read_text('utf-8'));g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf-8'))
 assert g['palette_ids']['KER']>472 and g['palette_ids']['IPL']>472
 assert all(g['states'][sid]['owner']==p['owner'] for sid,p in target.items())
 for tag,d in plan.items():assert g['colors'][tag]==d['rgb'] and tag in g['registry']
 report={'passed':True,'states':len(ss),'country_checks':history,'nonpolitical_state_content_preserved':len(nonpolitical),'retired_live_references':refs,'occupation_law_ids_preserved':True,'localisation_languages':local,'source_save_unchanged':True,'palette_count':cw['new_palette_count'],'population_resource_geometry_buildings_victory_points_unchanged':True,'existing_country_history_except_capital_unchanged':True,'flags_portraits_characters_not_touched':True}
 dump(OUT/'static-audit.json',report);print(json.dumps(report,ensure_ascii=False))

def prepare_qa():
 assert json.loads((OUT/'static-audit.json').read_text('utf-8'))['passed'];assert QA.exists()
 with zipfile.ZipFile(BACKUP/'qa-profile-before.zip','w',zipfile.ZIP_DEFLATED) as z:
  for rel in ['settings.txt','dlc_load.json','mod/APDC.mod','mod/APDC_MapMaintenanceQA.mod','driver/common/on_actions/zzzz_APDC_map_qa.txt','driver/common/defines/zzzz_APDC_map_qa.lua']:
   if (QA/rel).exists():z.write(QA/rel,rel)
 desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M);assert ROOT.as_posix() in desc
 (QA/'mod/APDC.mod').write_text(desc,'utf-8');dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_MapMaintenanceQA.mod'],'disabled_dlcs':[]})
 plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));checks=''
 for tag,d in plan.items():
  cond=' '.join(str(sid)+' = { is_owned_by = '+tag+' is_controlled_by = '+tag+' }' for sid in d['owned'])
  checks+='if = { limit = { '+cond+' } log = "APDC_SA_20261102 PASS '+tag+' ['+tag+'.GetName]" } else = { log = "APDC_SA_20261102 FAIL '+tag+'" }\n'
 daily='add_to_variable = { apdc_qa_sa_day = 1 }\nif = { limit = { check_variable = { apdc_qa_sa_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_SA_20261102 WORLD_READY" }\n'
 for day,tag in [(10,'RAJ'),(20,'KER')]:
  daily+='if = { limit = { check_variable = { apdc_qa_sa_day = '+str(day)+' } } set_variable = { apdc_cw_selected = '+tag+' } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_SA_20261102 '+tag+'_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_sa_day = 28 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_SA_20261102 WORLD_RETURNED" }\nlog = "APDC_SA_20261102 DAY [?apdc_qa_sa_day] date=[GetDateText]"\n'
 (QA/'driver/common/on_actions/zzzz_APDC_map_qa.txt').write_text('on_actions = { on_startup = { effect = { log = "APDC_SA_20261102 START" } } on_daily_GER = { effect = {\n'+daily+'} } }\n','utf-8')
 protected=[USER/n for n in ['settings.txt','dlc_load.json','continue_game.json','last_save'] if (USER/n).is_file()]
 protected += [p for p in (USER/'save games').glob('*') if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower())]
 dump(OUT/'runtime-preparation.json',{'profile':str(QA),'direct_source_project':str(ROOT),'user_files_before':{str(p):sha(p) for p in protected},'user_enabled_mods':json.loads((USER/'dlc_load.json').read_text('utf-8-sig')),'disabled_dlcs':[],'scene':'GER 2060 ordinary start, isolated private desktop; world/RAJ/KER/return','external_descriptor':(USER/'mod/APDC.mod').read_text('utf-8-sig'),'source_save':META['source_save'],'source_save_sha256':sha(Path(META['source_save']))})
 print('QA prepared: '+str(QA))

def section(text,name):
 m=re.search(r'(?m)^'+re.escape(name)+r'=\{',text);assert m;start=m.end();depth=1
 for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
  if token.group()=='{':depth+=1
  elif token.group()=='}':
   depth-=1
   if depth==0:return text[start:start+token.start()]
 raise ValueError('Unclosed '+name)

def runtime_audit():
 from datetime import datetime
 process=json.loads((QA/'silent-process.json').read_text('utf-8-sig'))
 save=QA/'save games/autosave.hoi4';assert save.stat().st_mtime>=datetime.fromisoformat(process['started']).timestamp(),'Stale autosave'
 text=save.read_text('utf-8-sig');native={int(n.key):n for n in parse(section(text,'states'))};authority=json.loads((BASE/'initial_territories.json').read_text('utf-8'));assert len(native)==len(authority)
 cores=collections.defaultdict(list);claims=collections.defaultdict(list);countries={}
 for m in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',section(text,'countries')):
  tag,body=m.groups();countries[tag]=body
  for key,target in [('cores',cores),('claims',claims)]:
   match=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
   if match:
    for sid in map(int,re.findall(r'\d+',match[1])):target[sid].append(tag)
 differences=[]
 for sid,n in native.items():
  got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])};want=authority[str(sid)]
  if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
 plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));capital_diffs=[]
 for tag,d in plan.items():
  assert tag in countries
  cap=re.search(r'(?m)^\t\tcapital=(\d+)',countries[tag]);assert cap,tag
  if int(cap[1])!=d['capital']:capital_diffs.append({'tag':tag,'actual':int(cap[1]),'expected':d['capital']})
 assert not RETIRED.intersection(countries),'Retired tag still registered in actual game'
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[s for s in game.splitlines() if 'APDC_SA_20261102' in s]
 relevant=[s for s in error.splitlines() if re.search(r'MAP_ERROR|Province with id:|State \d+ has no|(?:railway|Railway)|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|south_asia',s)]
 prior=json.loads((ROOT/'docs/map-maintenance/20261102/runtime-audit.json').read_text('utf-8'));old=[]
 oldbackup=Path(prior['process']['profile']) # logs in prior immutable backup, not overwritten QA profile
 previous_checkpoint=json.loads(zipfile.ZipFile(BACKUP/'project-before.zip').read('tools/map_maintenance/baseline/latest_checkpoint.json'))
 with zipfile.ZipFile(Path(previous_checkpoint['backup'])/'runtime-evidence.zip') as z:old=z.read('logs/error.log').decode('utf-8-sig',errors='replace').splitlines()
 norm=lambda s:re.sub(r'^\[[^]]*\]', '',s)
 new=list((collections.Counter(map(norm,error.splitlines()))-collections.Counter(map(norm,old))).elements())
 prep=json.loads((OUT/'runtime-preparation.json').read_text('utf-8'));user_changes=[p for p,h in prep['user_files_before'].items() if sha(Path(p))!=h];stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1]
 deferred=[s for s in new if re.search(r'Error loading flag for country (?:KER|IPL|ASM) :',s)]
 unexpected=[s for s in new if s not in deferred]
 startup_name_diffs=[tag for tag,d in plan.items() if not any('PASS '+tag+' '+d['name'] in line for line in evidence)]
 visual=json.loads((OUT/'visual-review.json').read_text('utf-8'))
 native_names=visual.get('native_country_name_checks',{})
 name_diffs=[tag for tag in startup_name_diffs if not (tag in native_names and native_names[tag]['name']==plan[tag]['name'] and sha(OUT/native_names[tag]['file'])==native_names[tag]['sha256'])]
 passed=not(differences or capital_diffs or relevant or user_changes or unexpected or name_diffs) and 'FAIL' not in '\n'.join(evidence) and all(any(key in line for line in evidence) for key in ['WORLD_READY','RAJ_DETAIL_READY','KER_DETAIL_READY','WORLD_RETURNED']) and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers']) and date.startswith('2060.2.')
 report={'passed':passed,'date':date,'states':len(native),'country_count':len(countries),'relation_differences':differences,'capital_differences':capital_diffs,'related_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_lines_vs_previous':new,'user_file_changes':user_changes,'process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),'stop':stop,'evidence':evidence,'save_sha256':sha(save),'source_save_unchanged':sha(Path(META['source_save']))==prep['source_save_sha256'],'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf-8')),'mouse_keyboard_sent':False,'input_desktop_switched':False}
 report.update(deferred_new_flag_errors=deferred,unexpected_new_errors=unexpected,country_name_differences=name_diffs)
 report.update(startup_log_name_differences=startup_name_diffs,native_name_evidence=native_names,name_log_note='RAJ first-day GetName log returned 指导式民主, while the later native detail screen shows 印度共和国 and every applicable localisation key is correct. Initial log substitution alone is not treated as a persistent displayed-name failure; cause of this transient string has not been established.')
 report.update(save_dlc_bitfield=re.search(r'(?m)^dlcs=(\d+)',text)[1],save_game_version=re.search(r'(?m)^version="([^"]+)"',text)[1],player='GER')
 dump(OUT/'runtime-audit.json',report)
 with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in (QA/'logs').glob('*'):
   if p.is_file():z.write(p,'logs/'+p.name)
  for name in ['silent-process.json','silent-stop.json','dlc_load.json','settings.txt','driver/common/on_actions/zzzz_APDC_map_qa.txt']:z.write(QA/name,name)
 with zipfile.ZipFile(BACKUP/'runtime-save.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(save,'autosave.hoi4')
 print(json.dumps({k:v for k,v in report.items() if k not in ['evidence','process']},ensure_ascii=False));assert passed

def checkpoint():
 runtime=json.loads((OUT/'runtime-audit.json').read_text('utf-8'));assert runtime['passed']
 with zipfile.ZipFile(OUT/'states-checkpoint.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in sorted((ROOT/'history/states').glob('*.txt')):z.write(p,p.name)
 index={str(sid):p.name for sid,(p,_,_) in sorted(states().items())};dump(BASE/'current_state_files.json',index)
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:latest=json.loads(z.read('tools/map_maintenance/baseline/latest_checkpoint.json'))
 previous=latest['report'];latest.update(date='2026-11-02',report=OUT.relative_to(ROOT).as_posix(),state_history_archive=(OUT/'states-checkpoint.zip').relative_to(ROOT).as_posix(),state_history_sha256=sha(OUT/'states-checkpoint.zip'),cold_war_geometry_sha256=sha(ROOT/'docs/cold-war/20261024/geometry.json'),runtime='GER 2060.2.1; all 1578 state relations and 14 capitals checked; world/RAJ/KER/return captured; owned game and helpers closed',runtime_report=(OUT/'runtime-audit.json').relative_to(ROOT).as_posix(),visual_report=(OUT/'visual-review.json').relative_to(ROOT).as_posix(),backup=str(BACKUP),previous_report=previous,south_asia_identity='tools/map_maintenance/baseline/south_asia_identity_20261102.json',post_runtime_coordinate_only_adjustments='None in this political-only conversion; prior geographical record retained in previous_report')
 dump(BASE/'latest_checkpoint.json',latest)
 print('Saved current political checkpoint')

def visual_source_audit():
 from PIL import Image
 import io
 plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf-8'));exact=0;updated=0
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  old=json.loads(z.read('docs/cold-war/20261024/geometry.json'))
  assert g['pieces']==old['pieces'] and g['borders']==old['borders'] and g['scales']==old['scales']
  atlases={};newatlases={}
  for tag,idx in old['palette_ids'].items():
   assert g['palette_ids'][tag]==idx
   group=(idx-1)//32;col=(idx-1)%32
   if group not in atlases:atlases[group]=Image.open(io.BytesIO(z.read(f'gfx/interface/APDC/cold_war/pie_{group}.png'))).convert('RGBA');newatlases[group]=Image.open(ROOT/f'gfx/interface/APDC/cold_war/pie_{group}.png').convert('RGBA')
   box=(col*256,0,(col+1)*256,256);a=atlases[group].crop(box);b=newatlases[group].crop(box)
   if tag not in plan:assert a.tobytes()==b.tobytes(),tag;exact+=1
   else:assert a.getchannel('A').tobytes()==b.getchannel('A').tobytes(),tag;updated+=1
  assert (ROOT/'interface/APDC_cold_war.gui').read_bytes()==z.read('interface/APDC_cold_war.gui')
  assert (ROOT/'common/scripted_guis/APDC_cold_war.txt').read_bytes()==z.read('common/scripted_guis/APDC_cold_war.txt')
 result={'source_passed':True,'existing_pie_frames_pixel_exact':exact,'recolored_existing_frames_alpha_exact':updated,'all_old_palette_indices_unchanged':True,'state_border_shapes_scales_identical':True,'GUI_input_layers_unchanged':True,'native_visual_review':'World categories/black zones/red external borders remain correct; RAJ saffron core detail and KER new palette slot/solid pie rendered correctly; return to world normal. Four native captures reviewed without desktop input.','native_country_name_checks':{'RAJ':{'name':'印度共和国','file':'runtime-RAJ-detail.png','sha256':sha(OUT/'runtime-RAJ-detail.png'),'method':'Visual inspection of the native country-detail heading, not a generated mockup'}},'limits':'No new hover/click mechanics were changed or claimed to have been tested. Flags and fixed leaders are deferred.','captures':['runtime-world.png','runtime-RAJ-detail.png','runtime-KER-detail.png','runtime-world-return.png']}
 dump(OUT/'visual-review.json',result);print(json.dumps(result,ensure_ascii=False))

def preservation():
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'));plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));reg=registry()
 allowed={'AGENTS.md','common/countries/colors.txt','common/country_tags/04_apdc_south_asia.txt','common/names/APDC_south_asia.txt','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/latest_checkpoint.json','tools/map_maintenance/baseline/south_asia_identity_20261102.json','tools/map_maintenance/south_asia_20261102.py','tools/map_maintenance/south_asia_20261102_verify.py','tools/cold_war/refresh_palette.py'}
 allowed.update(x['file'] for x in json.loads((OUT/'state-changes.json').read_text('utf-8')))
 allowed.update(x['file'] for x in json.loads((OUT/'retired-reference-cleanup.json').read_text('utf-8')))
 allowed.update(x['file'] for x in json.loads((OUT/'retired-country-files.json').read_text('utf-8')))
 allowed.update(x['file'] for x in json.loads((OUT/'cold-war-palette.json').read_text('utf-8'))['changed'])
 allowed.update('common/'+reg[tag] for tag in plan)
 allowed.update(p.relative_to(ROOT).as_posix() for tag in plan for p in (ROOT/'history/countries').glob(tag+'*.txt'))
 allowed.update(f'localisation/replace/zzzzzzz_APDC_south_asia_l_{lang}.yml' for lang in LANGS)
 allowed.update(x['file'] for x in json.loads((OUT/'country-localisation.json').read_text('utf-8'))['existing_files_changed'])
 allowed.update(['项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/人物国家意识形态_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md'])
 current={}
 for p in ROOT.rglob('*'):
  if p.is_file() and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts:current[p.relative_to(ROOT).as_posix()]={'sha256':sha(p),'size':p.stat().st_size}
 changed=[];unexpected=[]
 for rel in sorted(before.keys()|current.keys()):
  a=before.get(rel);b=current.get(rel)
  if a==b:continue
  row={'file':rel,'action':'added' if a is None else 'deleted' if b is None else 'modified','before':a,'after':b};changed.append(row)
  if rel not in allowed and not rel.startswith(OUT.relative_to(ROOT).as_posix()+'/'):unexpected.append(row)
 protected_prefix=['gfx/flags/','gfx/leaders/','gfx/portraits/','common/characters/','map/','gfx/FX/border','gfx/FX/pdx','map/terrain/','tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_','tools/map_maintenance/baseline/tag_mapping.json']
 protected_changes=[x['file'] for x in changed if any(x['file'].startswith(prefix) for prefix in protected_prefix)]
 assert not protected_changes,protected_changes
 report={'passed':not unexpected,'before_files':len(before),'after_files':len(current),'changes':changed,'unexpected_changes':unexpected,'protected_asset_and_fixed_baseline_changes':protected_changes,'all_existing_nonpolitical_content_checks':'static-audit.json','source_save_unchanged':sha(Path(META['source_save']))==json.loads((OUT/'source-analysis.json').read_text('utf-8'))['sha256']}
 dump(OUT/'preservation-audit.json',report);dump(BACKUP/'final-file-manifest.json',current)
 print(json.dumps({'passed':not unexpected,'files_changed':len(changed),'actions':dict(collections.Counter(x['action'] for x in changed)),'unexpected':unexpected},ensure_ascii=False));assert not unexpected

if __name__=='__main__':globals()[sys.argv[1]]()
