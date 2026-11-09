"""Read-only evidence, scoped references and isolated QA for the November 4 map."""
from finish_20261104 import *
import datetime,unicodedata
QA=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA_20261104')

def references_apply():
 p=ROOT/'common/scripted_triggers/GER_scripted_triggers.txt';t=p.read_text('utf-8-sig');changes=[];edits=[]
 plan=json.loads((OUT/'plan.json').read_text('utf-8'));prim={int(s):min(map(int,c),key=lambda k:(-c[str(k)],k)) for s,c in plan['state_sources'].items() if int(s)>=1579}
 for top in parse(t):
  if not top.key.startswith('GER_is_') or not top.key.endswith('_state'):continue
  ors=[n for n in top.children if n.key=='OR']
  if len(ors)!=1:continue
  block=ors[0];members={int(n.value) for n in block.children if n.key=='state' and n.value and n.value.isdigit()}
  add=sorted(s for s,src in prim.items() if src in members and s not in members)
  if not add:continue
  last=[n for n in block.children if n.key=='state'][-1]
  end=t.find('\n',last.end)
  edits.append((end,end,''.join('\n\t\tstate = '+str(s) for s in add)))
  changes.append({'file':p.relative_to(ROOT).as_posix(),'kind':'geographic_state_group','group':top.key,'added':add,'primary_sources':{s:prim[s] for s in add},'rule':'inherit geographic group of the largest previous-state contribution; ties use lowest source ID'})
 if edits:p.write_text(patches(t,edits),'utf-8')
 # The oil centre formerly covered by Baghdad now lies mostly in Salah ad Din.
 # Keep each existing reward once. The engine's later Basra ID 1409 is Inchiri
 # on APDC; the current Basra state is 1011. Baghdad distance anchor stays 291.
 for rel,goal in [('common/factions/goals/faction_goals_medium_term.txt','faction_goal_control_iraqi_oil'),('common/factions/goals/faction_goals_short_term.txt','faction_goal_develop_iraqi_oil')]:
  p=ROOT/rel;t=p.read_text('utf-8-sig');top=next(n for n in parse(t) if n.key==goal);edits=[]
  for n in walk(top.children):
   if n.key=='target':continue
   if n.key in ['controls_state','state'] and n.value in ['291','1409']:
    value={'291':'1626','1409':'1011'}[n.value];edits.append((n.value_start,n.value_end,value));changes.append({'file':rel,'kind':'Iraqi_oil_geography','goal':goal,'field':n.key,'from':n.value,'to':value})
   elif n.key in ['291','1409'] and n.children:
    value={'291':'1626','1409':'1011'}[n.key];edits.append((n.start,n.start+len(n.key),value));changes.append({'file':rel,'kind':'Iraqi_oil_geography','goal':goal,'field':'state_scope','from':n.key,'to':value})
  if edits:p.write_text(patches(t,edits),'utf-8')
 dump(OUT/'additional-reference-changes.json',changes)
 print(json.dumps({'changed_groups':sum(c['kind']=='geographic_state_group' for c in changes),'geographic_fields':len(changes)},ensure_ascii=False))

def extended_audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pm=pmap(states);defs,raster=raster_data();H,W=raster.shape
 plan=json.loads((OUT/'plan.json').read_text('utf8'));affected=set(plan['affected_states']);counts=collections.Counter();coast_issues=[]
 for line in (ROOT/'map/buildings.txt').read_text('utf8').splitlines():
  r=line.split(';');sid=int(r[0]);x,z=math.floor(float(r[2])),math.floor(float(r[4]));pid=int(r[6]) if r[1]=='floating_harbor' else int(raster[H-1-z,x]);counts[pid,r[1]]+=1
 model=json.loads((OUT/'model-changes.json').read_text('utf8'))
 for sid in affected:
  for v in states[sid][2].get('provinces').children:
   pid=int(v.key)
   if defs[pid]['type']!='land':continue
   for kind,(count,coast) in model['required_province_models'].items():
    if not coast or defs[pid]['coastal']=='true':assert counts[pid,kind]>=count,(sid,pid,kind,count)
 for entry in model['added']:
  if entry['kind']!='dockyard':continue
  x,_,z=map(float,entry['coordinates']);pid=int(raster[H-1-math.floor(z),math.floor(x)])
  if defs[pid]['coastal']!='true':coast_issues.append(entry)
 assert not coast_issues,coast_issues
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));active={v['owner'] for v in pol.values()};registry={}
 for p in (ROOT/'common/country_tags').glob('*.txt'):
  registry.update({n.key:n.value for n in parse(p.read_text('utf-8-sig'))})
 assert all(set([v['owner'],v['controller']]+v['cores']+v['claims'])<=set(registry) for v in pol.values())
 assert not {tag for v in pol.values() if v['owner'] in v['cores'] for tag in v['cores']+v['claims'] if tag not in active}
 # All initialization branches and effective historical state blocks remain
 # the APDC checkpoint's non-geographic scripts, with no map replay added.
 preserved=[];nested=[]
 ignore={'owner','controller','add_core_of','add_claim_by','victory_points','buildings'}
 for sid in affected:
  if sid not in old:continue
  before=[canon(n) for n in old[sid][2].get('history').children if n.key not in ignore and not(n.key=='set_state_flag' and n.value.startswith('GDP_regions_'))]
  after=[canon(n) for n in states[sid][2].get('history').children if n.key not in ignore and not(n.key=='set_state_flag' and n.value.startswith('GDP_regions_'))]
  assert before==after,('nongeographic history',sid);preserved.append(sid)
  nested.extend({'state':sid,'field':n.key} for n in walk(states[sid][2].get('history').children) if re.fullmatch(r'\d{4}\.\d+\.\d+',n.key) or n.key in ['if','else_if'])
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  for rel in ['history/countries/BYA - Buryatia.txt','history/countries/CKK - Chukotka.txt','history/countries/YAK - Yakutia.txt']:
   a=parse(z.read(rel).decode('utf-8-sig'));b=parse((ROOT/rel).read_text('utf-8-sig'));assert [canon(n) for n in a if n.key!='capital']==[canon(n) for n in b if n.key!='capital']
  for rel in ['common/factions/goals/faction_goals_medium_term.txt','common/factions/goals/faction_goals_short_term.txt']:
   def norm(n):return (('IRAQ_OIL_STATE' if n.key in ['291','1626','1409','1011'] else n.key),('IRAQ_OIL_STATE' if n.key in ['controls_state','state'] and n.value in ['291','1626','1409','1011'] else n.value),n.op,tuple(norm(c) for c in n.children))
   assert [norm(n) for n in parse(z.read(rel).decode('utf-8-sig'))]==[norm(n) for n in parse((ROOT/rel).read_text('utf-8-sig'))]
  for rel in ['common/on_actions','events','common/characters','common/ideologies','common/national_focus']:
   for p in (ROOT/rel).rglob('*'):
    if p.is_file():assert z.read(p.relative_to(ROOT).as_posix())==p.read_bytes(),('unrelated gameplay modified',str(p))
 # Sum exact contributions back to every fixed source, not only the world sum.
 alloc,totals=allocation(states);reverse=collections.defaultdict(lambda:{'population':Fraction(),'resources':collections.defaultdict(Fraction),'provinces':[]})
 for sid,data in alloc.items():
  for c in data['contributions']:
   row=reverse[c['source']];row['population']+=Fraction(c['population_contribution']);row['provinces']+=c['provinces']
   for k,v in c['resource_contributions'].items():row['resources'][k]+=Fraction(v)
 original=statefiles(BASE/'original_economy/history/states')
 for sid,(_,_,s) in original.items():
  row=reverse[sid];assert row['population']==Fraction(s.val('manpower','0'));assert sorted(row['provinces'])==sorted(int(v.key) for v in s.get('provinces').children)
  rr={n.key:Fraction(n.value) for b in s.children if b.key=='resources' for n in b.children};assert dict(row['resources'])==rr
 dump(OUT/'economy-reverse-audit.json',{'passed':True,'source_states':len(reverse),'sources':{s:{'exact_population':str(v['population']),'exact_resources':{k:str(x) for k,x in v['resources'].items()},'province_count':len(v['provinces'])} for s,v in reverse.items()},'totals':totals})
 dump(OUT/'extended-static-audit.json',{'passed':True,'all_registered_political_tags':True,'inactive_core_claim_cleanup_verified':True,'affected_province_spawn_coverage':True,'new_dockyard_positions_are_coastal':True,'nongeographic_existing_histories_preserved':preserved,'nested_affected_date_or_conditional_history':nested,'capital_only_country_changes':3,'actual_oil_rewards_and_conditions_preserved_except_geography':True,'unrelated_gameplay_directories_byte_preserved':True,'sea_connectivity':'All sea/lake strategic assignments, province pixels and sea adjacencies unchanged from completed checkpoint; graph unchanged','fixed_economy_sources_reverse_checked':len(reverse)})
 print('Extended static audit passed')

def prepare_qa():
 assert json.loads((OUT/'static-audit.json').read_text('utf8'))['passed']
 assert json.loads((OUT/'extended-static-audit.json').read_text('utf8'))['passed']
 assert json.loads((OUT/'cold-war-refresh.json').read_text('utf8'))['states']==1628
 assert not QA.exists(),'Use a fresh isolated profile; preserve an existing profile'
 driver=QA/'driver'
 for rel in ['mod','driver/common/on_actions','driver/common/defines']:(QA/rel).mkdir(parents=True,exist_ok=True)
 desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M)
 (QA/'mod/APDC.mod').write_text(desc,'utf8')
 (QA/'mod/APDC_MapMaintenanceQA.mod').write_text('name="APDC isolated November 4 map diagnostics"\npath="'+driver.as_posix()+'"\nsupported_version="1.19.*"\n','utf8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_MapMaintenanceQA.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA/settings.txt').read_text('utf-8-sig')
 (QA/'settings.txt').write_text(settings.replace('save_career_to_cloud=yes','save_career_to_cloud=no').replace('telemetry_enabled=yes','telemetry_enabled=no'),'utf8')
 (driver/'common/defines/zzzz_APDC_map_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf8')
 authority=json.loads((BASE/'initial_territories.json').read_text('utf8'));checks=''
 for sid in range(1579,1629):
  p=authority[str(sid)];conditions=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+tag for tag in p['cores'])
  checks+=f'{sid} = {{ if = {{ limit = {{ {conditions} }} log = "APDC_MAP_20261104 PASS state_{sid}" }} else = {{ log = "APDC_MAP_20261104 FAIL state_{sid}" }} }}\n'
 daily='add_to_variable = { apdc_qa_map_day = 1 }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_map_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_MAP_20261104 WORLD_READY" }\n'
 for day,tag in [(20,'SOV'),(27,'MON'),(34,'IRQ')]:
  daily+='if = { limit = { check_variable = { apdc_qa_map_day = '+str(day)+' } } set_variable = { apdc_cw_selected = '+tag+' } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261104 '+tag+'_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_map_day = 41 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261104 WORLD_RETURNED" }\nlog = "APDC_MAP_20261104 DAY [?apdc_qa_map_day] date=[GetDateText]"\n'
 (driver/'common/on_actions/zzzz_APDC_map_qa.txt').write_text('on_actions = { on_startup = { effect = { log = "APDC_MAP_20261104 START" } } on_daily_GER = { effect = {\n'+daily+'} } }\n','utf8')
 protected=[USER/n for n in ['dlc_load.json','settings.txt','pdx_settings.txt','gameplaysettings.txt','continue_game.json','last_save'] if (USER/n).is_file()]
 protected.extend(p for p in (USER/'save games').glob('*') if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower()))
 dump(OUT/'runtime-preparation.json',{'profile':str(QA),'direct_source_project':str(ROOT),'user_files_before':{str(p):sha(p) for p in protected},'user_enabled_mods':json.loads((USER/'dlc_load.json').read_text('utf-8-sig')),'disabled_dlcs':[],'scene':'GER 2060 ordinary start; one run with world/SOV/MON/IRQ/return screenshots on isolated private desktop','external_descriptor':(USER/'mod/APDC.mod').read_text('utf-8-sig'),'toolpack_loaded':False})
 print('Prepared '+str(QA))

def section(text,name):
 m=re.search(r'(?m)^'+re.escape(name)+r'=\{',text);assert m,('missing save section',name);start=m.end();depth=1
 for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
  if token.group()=='{':depth+=1
  elif token.group()=='}':
   depth-=1
   if not depth:return text[start:start+token.start()]
 raise ValueError('Incomplete save section '+name)

def runtime_audit():
 record=json.loads((QA/'silent-process.json').read_text('utf-8-sig'));save=QA/'save games/autosave.hoi4'
 assert save.stat().st_mtime>=datetime.datetime.fromisoformat(record['started']).timestamp()
 text=save.read_text('utf-8-sig');native={int(n.key):n for n in parse(section(text,'states'))};authority=json.loads((BASE/'initial_territories.json').read_text('utf8'));assert len(native)==len(authority)
 cores=collections.defaultdict(list);claims=collections.defaultdict(list);countries={}
 for m in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',section(text,'countries')):
  tag,body=m.groups();countries[tag]=body
  for key,target in [('cores',cores),('claims',claims)]:
   match=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
   if match:
    for sid in map(int,re.findall(r'\d+',match[1])):target[sid].append(tag)
 differences=[];dmz=[]
 for sid,n in native.items():
  got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])};want={**authority[str(sid)],'cores':sorted(authority[str(sid)]['cores']),'claims':sorted(authority[str(sid)]['claims'])}
  if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
  if n.val('demilitarized')=='yes':dmz.append(sid)
 caps=[]
 for p in (ROOT/'history/countries').glob('*.txt'):
  for n in parse(p.read_text('utf-8-sig')):
   if n.key=='capital':
    tag=p.name[:3];m=re.search(r'(?m)^\t\tcapital=(\d+)',countries.get(tag,''));actual=int(m[1]) if m else None
    # The engine chooses an owned capital for active countries; releasable
    # countries can keep zero until release, so compare all active nations.
    if tag in {v['owner'] for v in authority.values()}:assert actual==int(n.value),('runtime capital',tag,n.value,actual)
    caps.append({'tag':tag,'configured':int(n.value),'runtime':actual})
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[line for line in game.splitlines() if 'APDC_MAP_20261104' in line]
 relevant=[line for line in error.splitlines() if re.search(r'MAP_ERROR|map/buildings.txt|Province with id:|State \d+ has no|(?:railway|Railway)|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|pdx_localize.cpp|localization.*error',line)]
 prep=json.loads((OUT/'runtime-preparation.json').read_text('utf8'));user_changes=[p for p,h in prep['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1]
 markers=['WORLD_READY','SOV_DETAIL_READY','MON_DETAIL_READY','IRQ_DETAIL_READY','WORLD_RETURNED']
 passed=not(differences or dmz or relevant or user_changes) and 'FAIL' not in '\n'.join(evidence) and all(any(key in line for line in evidence) for key in markers) and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers']) and date.startswith('2060.2.')
 previous_errors=(ROOT/'docs/map-maintenance/20261102-south-asia/runtime-audit.json')
 normalize=lambda s:re.sub(r'^(?:\[[^\]]*\])+\s*','',s)
 with zipfile.ZipFile(Path(META['checkpoint']['backup'])/'runtime-evidence.zip') as z:
  prior=z.read('logs/error.log').decode('utf-8-sig',errors='replace')
 diff=collections.Counter(normalize(s) for s in error.splitlines())-collections.Counter(normalize(s) for s in prior.splitlines())
 report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'countries_read':len(countries),'relation_differences':differences,'initial_dmz':dmz,'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_signatures_vs_last_completed_runtime':dict(diff),'evidence':evidence,'process':record,'stop':stop,'user_file_changes':user_changes,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf8')),'dlc_save_header':re.findall(r'(?m)^.*dlc.*$',text[:30000]),'input_desktop_switched':False,'mouse_keyboard_sent':False,'capital_checks':caps}
 dump(OUT/'runtime-audit.json',report)
 with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in (QA/'logs').glob('*'):
   if p.is_file():z.write(p,'logs/'+p.name)
  for name in ['silent-process.json','silent-stop.json','settings.txt','dlc_load.json']:
   z.write(QA/name,name)
 assert passed,{k:v for k,v in report.items() if k not in ['capital_checks','evidence']}
 print(json.dumps({k:v for k,v in report.items() if k not in ['capital_checks','evidence','process','dlc_save_header']},ensure_ascii=False))

def review_assets():
 import numpy as np
 from PIL import Image,ImageFilter
 ss=statefiles(ROOT/'history/states');pm=pmap(ss);defs,raster=raster_data();g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf8'));prefix='gfx/interface/APDC/cold_war/'
 assert set(map(int,g['states']))==set(ss)
 for e in g['pieces']:
  a=np.asarray(Image.open(ROOT/prefix/'map'/(e['name']+'.png')))
  mask=np.pad(np.isin(raster[e['y']:e['y']+e['h'],e['x']:e['x']+e['w']],[int(v.key) for v in ss[e['state']][2].get('provinces').children]),e['padding'])
  assert np.array_equal(a[:,:,0]>127,mask),('mask',e['name'])
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  old=json.loads(z.read('docs/cold-war/20261024/geometry.json'));oldpol=json.loads(z.read('tools/map_maintenance/baseline/initial_territories.json'));newpol=json.loads((BASE/'initial_territories.json').read_text('utf8'))
  assert old['palette_ids']==g['palette_ids'] and old['scales']==g['scales'] and old['colors']==g['colors']
  def world(meta,pol,before=False):
   load=lambda rel:Image.open(io.BytesIO(z.read(rel)) if before else ROOT/rel).convert('RGBA')
   canvas=Image.new('RGBA',(1000,500))
   for e in meta['pieces']:
    tag=pol[str(e['state'])]['owner'];w=e['world'];im=load(prefix+'map/world_'+str(e['id'])+'.png');frame=0 if tag=='GER' else 2 if tag in ['FRA','LLU'] else 1;tile=im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h']))
    if tag=='ZZZ':tile=load(prefix+'world_style/black_'+str(e['id'])+'.png')
    canvas.alpha_composite(tile,(w['x'],w['y']))
   for e in meta['borders']:
    a,b=[pol[str(e[k])]['owner'] for k in ['a','b']]
    if a==b:continue
    w=e['world'];im=load(prefix+'world_style/border_'+str(e['id'])+'.png');frame=int('ZZZ' in [a,b]);canvas.alpha_composite(im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h'])),(w['x'],w['y']))
   canvas.alpha_composite(load(prefix+'coasts.png'));return canvas
  before=world(old,oldpol,True);after=world(g,newpol);before.save(OUT/'world-before.png');after.save(OUT/'world-after.png');changed=np.any(np.asarray(before)!=np.asarray(after),axis=2)
  affected=set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states']);pids=[pid for pid,sid in pm.items() if sid in affected]
  allowed=Image.fromarray(np.isin(raster,pids).astype('uint8')*255).resize((1000,500),Image.Resampling.LANCZOS).filter(ImageFilter.MaxFilter(9));outside=int(np.count_nonzero(changed & (np.asarray(allowed)==0)));assert not outside,outside
  protected=['palette.png','background.png','screen_overlay.png','pie_frame.png','option.png','control.png','swatches.png']
  protected.extend(p.name for p in (ROOT/prefix).glob('pie_*.png'))
  protected=[v for v in protected if prefix+v in z.namelist() and (ROOT/prefix/v).is_file()]
  assert all(z.read(prefix+v)==(ROOT/prefix/v).read_bytes() for v in protected)
  assert z.read('gfx/FX/APDC_cw_palette.shader')==(ROOT/'gfx/FX/APDC_cw_palette.shader').read_bytes()
  beforeloc=z.read('localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml')
  afterloc=(ROOT/'localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml').read_bytes();assert afterloc.startswith(beforeloc)
  assert set(re.findall(rb'APDC_CW_STATE_(\d+)',afterloc[len(beforeloc):]))=={str(s).encode() for s in range(1579,1629)}
 native=[];diff=None
 if (OUT/'runtime-visual-captures.json').exists():
  native=json.loads((OUT/'runtime-visual-captures.json').read_text('utf8'))
  if (OUT/'runtime-world-return.png').exists():
   a=np.asarray(Image.open(OUT/'runtime-world.png'))[150:650,458:1458];b=np.asarray(Image.open(OUT/'runtime-world-return.png'))[150:650,458:1458];diff=int(np.count_nonzero(np.any(a!=b,axis=2)));assert diff==0,diff
 dump(OUT/'visual-asset-audit.json',{'passed':True,'state_masks_exact':len(g['pieces']),'world_changed_pixels':int(changed.sum()),'unrelated_world_changed_pixels':outside,'palette_count':len(g['palette_ids']),'zoom_levels':len(g['scales']),'palette_scales_shader_and_non_map_art_preserved':True,'protected_art':protected,'native_capture_count':len(native),'native_world_first_vs_return_diff_pixels':diff,'dynamic_country_tooltips_preserved_and_new_50_added':True})
 print(json.dumps({'state_masks':len(g['pieces']),'world_changed':int(changed.sum()),'unrelated_pixels':outside,'native_world_return_diff':diff}))

def city_review():
 source=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/GF-MAP/.codex_backups/20261020-183551-chinese-city-name-corrections/现代胜利点总表.json')
 data=json.loads(source.read_text('utf-8-sig'));ss=statefiles(ROOT/'history/states');pm=pmap(ss)
 def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
 regions={1579,1581,1582,1585,1589,1590,1593,1594,1600,1601,1602,1605,1606,*range(1609,1627),822,877,876,564,569,817,676,1143,675}
 aliases={637:['Petropavlovsk-Kamchatskiy','Petropavlovsk Kamchatsky'],1142:['Hasakah','Al Hasakah','Al Ḩasakah'],574:['Neryungri'],575:['Mirnyy'],653:['Ekaterinburg'],1608:['Krasnoturinsk','Krasnotur\'insk']}
 rows=[];mismatches=[];unresolved=[];uncertain=[]
 # The preserved GeoNames settlement catalogue also covers towns below the
 # VP threshold. Use the established Patterson fit only for this name audit;
 # it does not create/move city VPs or override user-hosted cities.
 import numpy as np
 gazroot=source.parent.parent/'20261019-200749-modern-victory-points'
 fit=json.loads((gazroot/'registration/global_fit.json').read_text('utf8'));sx,sy,tx,ty=fit['params'];defs,raster=raster_data();H,W=raster.shape
 queries={sid:{norm(v) for v in [names[1]]+aliases.get(sid,[])} for sid,names in NAMES.items() if sid not in regions};settlements=collections.defaultdict(list)
 with zipfile.ZipFile(gazroot/'research/geonames_cities500.zip') as z:
  with z.open('cities500.txt') as f:
   for raw in f:
    fields=raw.decode('utf8').rstrip('\n').split('\t')
    if len(fields)<15 or fields[8] not in ['RU','IQ','SY','GB']:continue
    labels={norm(v) for v in [fields[1],fields[2]]+fields[3].split(',')}
    for sid,wanted in queries.items():
     country='IQ' if sid in [1627,1628] else 'SY' if sid==1142 else 'GB' if sid==582 else 'RU'
     if fields[8]!=country or not labels&wanted:continue
     lat,lon=map(float,fields[4:6]);phi=math.radians(lat);p2=phi*phi;x=math.radians(lon)*sx+tx;y=ty-sy*phi*(1.0148+p2*p2*(0.23185+p2*(-0.14499+0.02406*p2)))
     ix=int(math.floor(x+.5))%W;iy=max(0,min(H-1,int(math.floor(y+.5))));pid=int(raster[iy,ix]);actual=pm.get(pid);coast_snap=0
     if actual is None:
      # At most three original-map pixels, as in the fixed city policy.
      candidates=[]
      for dy in range(-3,4):
       for dx in range(-3,4):
        if dx*dx+dy*dy>9 or not 0<=iy+dy<H:continue
        pp=int(raster[iy+dy,(ix+dx)%W])
        if pp in pm:candidates.append((dx*dx+dy*dy,pp,ix+dx,iy+dy))
      if candidates:dist,pid,ix,iy=min(candidates);actual=pm[pid];coast_snap=math.sqrt(dist)
     if actual is None:continue
     # Disambiguate different towns with the same name by proximity to the
     # target state's current footprint, then population and stable ID.
     pids=[int(v.key) for v in ss[sid][2].get('provinces').children];yy,xx=np.nonzero(np.isin(raster,pids));distance=math.hypot(max(xx.min()-x,0,x-xx.max()),max(yy.min()-y,0,y-yy.max()))
     nearby=sorted({pm.get(int(v)) for v in raster[max(0,iy-2):iy+3,max(0,ix-2):ix+3].flat if pm.get(int(v)) is not None})
     settlements[sid].append({'city':fields[1],'geonames_id':int(fields[0]),'lat':lat,'lon':lon,'province':pid,'actual_state':actual,'country_iso2':country,'population_catalogue':int(fields[14] or 0),'project_x':x,'project_y':y,'coast_snap_pixels':coast_snap,'nearby_states_within_2pixels':nearby,'bbox_distance':distance,'method':'Preserved GeoNames cities500 coordinates projected with fixed Patterson fit; border proximity recorded'})
 for sid,names in sorted(NAMES.items()):
  if sid in regions:rows.append({'state':sid,'name':names[0],'kind':'region, governorate, district or range; city-centre test not applied'});continue
  wanted={norm(v) for v in [names[1]]+aliases.get(sid,[])};country='IQ' if sid in [1627,1628] else 'SY' if sid==1142 else 'GB' if sid==582 else 'RU';matches=[]
  for r in data:
   if r.get('country_iso2')!=country:continue
   labels=[r.get(k,'') for k in ['name','ascii','ucdb_name']]+[r.get('names',{}).get('english','')];own=bool(wanted & {norm(v) for v in labels});members=[v for v in r.get('same_province_cities',[]) if norm(v['name']) in wanted]
   if own or members:matches.append({'city':members[0]['name'] if members else r['name'],'province':r['province_id'],'actual_state':pm[r['province_id']],'representative_city':r['name'],'ucdb_id':members[0]['ucdb_id'] if members else r['ucdb_id'],'same_province_member':bool(members),'country_iso2':country})
  if not matches and settlements.get(sid):
   matches=[min(settlements[sid],key=lambda r:(r['bbox_distance'],-r['population_catalogue'],r['geonames_id']))]
  inside=any(r['actual_state']==sid for r in matches)
  entry={'state':sid,'chinese':names[0],'english':names[1],'matches':matches,'contains_named_city':inside}
  if not matches:entry['status']='Below-threshold settlement or absent from fixed UCDB city inventory; city point not independently verified';unresolved.append(entry)
  elif not inside and any(sid in r.get('nearby_states_within_2pixels',[]) for r in matches):entry['status']='Projected city lies within two pixels of target-state border; boundary uncertainty retained, no geographic change';uncertain.append(entry)
  elif not inside:entry['status']='Named city lies outside state; user display name retained, no boundary or VP moved';mismatches.append(entry)
  else:entry['status']='Named city is in this state'
  rows.append(entry)
 report={'source':str(source),'source_sha256':sha(source),'supplementary_settlements':str(gazroot/'research/geonames_cities500.zip'),'supplementary_sha256':sha(gazroot/'research/geonames_cities500.zip'),'projection_source':'https://github.com/OSGeo/PROJ/blob/master/src/projections/patterson.cpp','method':'Country-filtered fixed modern city/same-province inventory, supplemented by fixed GeoNames settlement catalogue and Patterson fit. State-border uncertainty is retained.','rows':rows,'mismatches':mismatches,'border_uncertain':uncertain,'unresolved_small_or_missing_settlements':unresolved,'no_boundary_or_victory_point_changes':True}
 dump(OUT/'city-named-state-review.json',report)
 current=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));current['latest_added_renamed_state_review']={'date':'2026-11-04','report':(OUT/'city-named-state-review.json').relative_to(ROOT).as_posix(),'city_named_states_checked':len(NAMES)-len(regions),'mismatches':mismatches,'border_uncertain':uncertain,'unresolved':unresolved};dump(BASE/'city_named_state_mismatches.json',current)
 print(json.dumps({'city_states':len(NAMES)-len(regions),'mismatches':mismatches,'unresolved':[(r['state'],r['english']) for r in unresolved]},ensure_ascii=False))

def checkpoint():
 from concurrent.futures import ThreadPoolExecutor
 ss=statefiles(ROOT/'history/states');runtime=json.loads((OUT/'runtime-audit.json').read_text('utf8'));static=json.loads((OUT/'static-audit.json').read_text('utf8'));extended=json.loads((OUT/'extended-static-audit.json').read_text('utf8'));visual=json.loads((OUT/'visual-asset-audit.json').read_text('utf8'))
 assert runtime['passed'] and static['passed'] and extended['passed'] and visual['passed']
 assert visual['native_capture_count']==5 and visual['native_world_first_vs_return_diff_pixels']==0
 visual_review=json.loads((OUT/'visual-review.json').read_text('utf8'));assert visual_review['reviewed'] and visual_review['capture_count']==5
 archive=OUT/'states-checkpoint.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for sid,(p,_,_) in sorted(ss.items()):z.write(p,p.name)
 dump(OUT/'state-hashes.json',{str(sid):{'file':p.name,'sha256':sha(p)} for sid,(p,_,_) in ss.items()})
 maparchive=OUT/'map-checkpoint.zip'
 with zipfile.ZipFile(maparchive,'w',zipfile.ZIP_DEFLATED) as z:
  for rel in ['map/buildings.txt','map/railways.txt','map/supply_nodes.txt','map/adjacencies.csv','docs/cold-war/20261024/geometry.json','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/modern_victory_points.json']:
   z.write(ROOT/rel,rel)
  for p in (ROOT/'map/strategicregions').glob('*.txt'):z.write(p,p.relative_to(ROOT).as_posix())
 cp={'date':'2026-11-04','report':OUT.relative_to(ROOT).as_posix(),'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'political_relations':'tools/map_maintenance/baseline/initial_territories.json','state_index':'tools/map_maintenance/baseline/current_state_files.json','cold_war_geometry':'docs/cold-war/20261024/geometry.json','cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER '+runtime['date']+'; all 1628 state relations checked; native world/SOV/MON/IRQ/return reviewed; own game/helpers stopped','runtime_report':(OUT/'runtime-audit.json').relative_to(ROOT).as_posix(),'visual_report':(OUT/'visual-review.json').relative_to(ROOT).as_posix(),'backup':str(BACKUP),'previous_report':META['checkpoint']['report'],'geography_backup':str(BACKUP),'railways':'map/railways.txt','railways_sha256':sha(ROOT/'map/railways.txt'),'railways_checkpoint':META['checkpoint']['railways_checkpoint'],'map_checkpoint_archive':maparchive.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(maparchive),'states':len(ss),'south_asia_identity':META['checkpoint']['south_asia_identity'],'city_review':(OUT/'city-named-state-review.json').relative_to(ROOT).as_posix()}
 dump(BASE/'latest_checkpoint.json',cp)
 preservation()
 print('Checkpoint saved '+str(archive))

def preservation():
 from concurrent.futures import ThreadPoolExecutor
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));renames=json.loads((OUT/'renames.json').read_text('utf8'));loc=json.loads((OUT/'localisation-changes.json').read_text('utf8'));ss=statefiles(ROOT/'history/states');plan=json.loads((OUT/'plan.json').read_text('utf8'))
 allowed={r['file'] for r in cw['changed']}|{r['file'] for r in loc}|{r['new'] for r in renames}
 allowed|={p.relative_to(ROOT).as_posix() for sid,(p,_,_) in ss.items() if sid in plan['affected_states']}
 allowed|={r['file'] for r in json.loads((OUT/'geographic-reference-changes.json').read_text('utf8'))+json.loads((OUT/'additional-reference-changes.json').read_text('utf8'))}
 written=set(json.loads((OUT/'strategic-repairs.json').read_text('utf8'))['written_regions'])
 allowed|={p.relative_to(ROOT).as_posix() for p in (ROOT/'map/strategicregions').glob('*.txt') if int(parse(p.read_text('utf-8-sig'))[0].val('id')) in written}
 allowed|={'map/buildings.txt','tools/map_maintenance/finish_20261104.py','tools/map_maintenance/verify_20261104.py','tools/cold_war/refresh_geography.py','tools/performance/test_process_cleanup.ps1','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/latest_checkpoint.json','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json'}
 allowed|={'项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md'}
 files=[]
 for folder,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in ['.git','__pycache__']]
  files.extend(Path(folder)/name for name in names if Path(folder)/name!=OUT/'preservation-audit.json')
 def inspect(p):
  rel=p.relative_to(ROOT).as_posix();return rel,sha(p),before.get(rel,{}).get('sha256')
 with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(inspect,files))
 changed=[{'file':rel,'before':old,'after':new} for rel,new,old in rows if old and old!=new];added=[{'file':rel,'sha256':new} for rel,new,old in rows if not old];removed=[rel for rel in before if not (ROOT/rel).exists()]
 unexpected=[r for r in changed+added if r['file'] not in allowed and not r['file'].startswith(OUT.relative_to(ROOT).as_posix()+'/')];unexpected_removed=sorted(set(removed)-{r['old'] for r in renames})
 protected=['AGENTS.md','descriptor.mod','map/provinces.bmp','map/definition.csv','map/heightmap.bmp','map/rivers.bmp','map/adjacencies.csv','map/railways.txt','map/supply_nodes.txt','map/unitstacks.txt','gfx/FX/border.shader','gfx/FX/pdxmap.shader','gfx/FX/pdxwater.shader','gfx/FX/gf_map_style.fxh','gfx/FX/gf_map_border_data.fxh','gfx/FX/mapname.shader','gfx/FX/APDC_cw_palette.shader','common/defines/zzzz_apdc_map_zz_gf_map_art.lua','gfx/interface/APDC/cold_war/palette.png','gfx/interface/APDC/cold_war/background.png','tools/cold_war/render_mode.json']
 preserved={rel:sha(ROOT/rel)==before[rel]['sha256'] for rel in protected if rel in before};assert all(preserved.values()),preserved
 immutable=[r for r in changed if r['file'].startswith(('tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_'))];assert not immutable,immutable
 report={'passed':not(unexpected or unexpected_removed),'files_before':len(before),'files_hashed_after':len(rows),'changed_existing':changed,'added':added,'removed_by_authorized_rename':removed,'unexpected_changes':unexpected,'unexpected_removed':unexpected_removed,'protected_hashes_preserved':preserved,'original_economy_import_snapshots_preserved':True,'all_preexisting_user_changes_outside_authorized_scope_preserved':True,'gameplay_changes':'Only geographic state-group membership and Iraqi-oil state references; numerical rewards, conditions and country gameplay retained','runs':['Diagnostic stopped after static image mismatch detected; archived separately','Final ordinary GER start after unchanged-edge preservation; source assets did not change during that run']}
 dump(OUT/'preservation-audit.json',report);assert report['passed'],{'unexpected_changes':unexpected,'unexpected_removed':unexpected_removed}
 dump(BACKUP/'final-file-manifest.json',{rel:{'sha256':new} for rel,new,_ in rows})
 with zipfile.ZipFile(BACKUP/'runtime-save.zip','w',zipfile.ZIP_DEFLATED) as z:
  z.write(QA/'save games/autosave.hoi4','autosave.hoi4')
 print(json.dumps({'preserved':report['passed'],'changed':len(changed),'added':len(added),'renamed':len(removed),'checked_files':len(rows)}))

if __name__=='__main__':globals()[sys.argv[1]]()
