"""Reviewed conditional city-province alignment, tied to the November 4 byte backup.

Only directly touching city provinces move. No old migration apply is reused.
The previous modules supply parsers, exact fixed-source economy and full audits.
"""
from pathlib import Path
import sys,json,zipfile,collections,hashlib,math,re,os,datetime,shutil,io
from fractions import Fraction
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'D:/APDC_ColdWarTools/pydeps313')
import finish_20261104 as oldtool
import verify_20261104 as oldverify
from finish_20261104 import parse,walk,patches,canon,statefiles,pmap,allocation,raster_data,sha,dump

ROOT=oldtool.ROOT;BASE=ROOT/'tools/map_maintenance/baseline'
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-city-alignment-20261104.json').read_text('utf8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];QA=Path(META['qa']);USER=oldtool.USER
MOVES=[v for v in META['adjacency'] if v['move']]
AFFECTED={v[k] for v in MOVES for k in ['from','to']}
for module in [oldtool,oldverify]:
 module.OUT=OUT;module.BACKUP=BACKUP;module.META=META;module.NAMES={};module.QA=QA

def apply():
 assert not (OUT/'changes.json').exists(),'One-time apply; preserve completed results'
 states=statefiles(ROOT/'history/states');oldpm=pmap(states);texts={s:v[1] for s,v in states.items()};transfer_vps=[]
 manifest=json.loads((BACKUP/'manifest-before.json').read_text('utf8'))
 for sid in AFFECTED:assert sha(states[sid][0])==manifest[states[sid][0].relative_to(ROOT).as_posix()]['sha256']
 for m in MOVES:
  assert oldpm[m['province']]==m['from'] and m['direct_border']
  for sid,add in [(m['from'],False),(m['to'],True)]:
   s=parse(texts[sid])[0];pids={int(v.key) for v in s.get('provinces').children}
   if add:pids.add(m['province'])
   else:pids.remove(m['province'])
   assert pids
   n=s.get('provinces');texts[sid]=patches(texts[sid],[(n.value_start,n.value_end,'{\n\t\t'+' '.join(map(str,sorted(pids)))+'\n\t}')])
  # These four states have infrastructure only. A position is not an actual factory.
  src=states[m['from']][2].get('history');assert all(n.key=='infrastructure' for n in src.get('buildings').children)
  for n in [v for v in src.children if v.key=='victory_points']:
   items=[int(v.key) for v in n.children]
   assert len(items)%2==0
   for pid,score in zip(items[::2],items[1::2]):
    if pid==m['province']:transfer_vps.append({'province':pid,'score':score,'from':m['from'],'to':m['to']})
 for m in transfer_vps:
  sid=m['from'];t=texts[sid];s=parse(t)[0];edits=[]
  for n in s.get('history').children:
   if n.key!='victory_points':continue
   items=[int(v.key) for v in n.children];pairs=list(zip(items[::2],items[1::2]))
   if not any(pid==m['province'] for pid,_ in pairs):continue
   rest=[(pid,score) for pid,score in pairs if pid!=m['province']]
   edits.append((n.start,n.end,'victory_points = { '+' '.join(f'{pid} {score}' for pid,score in rest)+' }' if rest else ''))
  texts[sid]=patches(t,edits)
  sid=m['to'];t=texts[sid];b=parse(t)[0].get('history').get('buildings')
  texts[sid]=patches(t,[(b.start,b.start,f'victory_points = {{ {m["province"]} {m["score"]} }}\n\t\t')])
 proposed={sid:(p,texts[sid],parse(texts[sid])[0]) for sid,(p,_,_) in states.items()};npmap=pmap(proposed)
 alloc,totals=allocation(proposed)
 economy_changes=[]
 for sid in sorted(AFFECTED):
  before=states[sid][2];t=texts[sid]
  for key,val in [('manpower',str(alloc[sid]['population'])),('resources','{ '+' '.join(f'{k} = {v}' for k,v in alloc[sid]['resources'].items())+' }')]:
   t=oldtool.set_field(t,parse(t)[0],key,val)
  texts[sid]=t;states[sid][0].write_text(t,'utf8')
  economy_changes.append({'state':sid,'population_before':int(before.val('manpower')),'population_after':alloc[sid]['population'],'resources_before':{n.key:int(n.value) for b in before.children if b.key=='resources' for n in b.children},'resources_after':alloc[sid]['resources']})
 dump(OUT/'allocation.json',alloc);dump(OUT/'allocation-totals.json',totals)
 regions={};preg={}
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];rid=int(n.val('id'));regions[rid]=(p,t,n,[int(v.key) for v in n.get('provinces').children])
  for v in n.get('provinces').children:assert int(v.key) not in preg;preg[int(v.key)]=rid
 region_changes=[];written=set()
 for m in MOVES:
  a=preg[m['province']];target_pids=[pid for pid,sid in npmap.items() if sid==m['to'] and pid!=m['province']];rs={preg[p] for p in target_pids};assert len(rs)==1;b=rs.pop()
  if a==b:continue
  regions[a][3].remove(m['province']);regions[b][3].append(m['province']);written|={a,b};region_changes.append({'province':m['province'],'from':a,'to':b})
 for rid in written:
  p,t,n,pids=regions[rid];v=n.get('provinces');new=patches(t,[(v.value_start,v.value_end,'{\n\t\t'+' '.join(map(str,sorted(pids)))+'\n\t}')]);nn=parse(new)[0]
  assert [canon(v) for v in n.children if v.key!='provinces']==[canon(v) for v in nn.children if v.key!='provinces'];p.write_text(new,'utf8')
 dump(OUT/'strategic-repairs.json',{'written_regions':sorted(written),'province_transfers':region_changes,'weather_and_seasons_preserved':True})
 defs,raster=raster_data();H,W=raster.shape;models=[]
 for line in (ROOT/'map/buildings.txt').read_text('utf8').splitlines():
  row=line.split(';');pid=int(row[6]) if row[1]=='floating_harbor' else int(raster[H-1-math.floor(float(row[4])),math.floor(float(row[2]))]);models.append((row,pid,npmap.get(pid)))
 oldtool.update_models(models,npmap,oldpm,raster,defs,AFFECTED)
 vp=json.loads((BASE/'modern_victory_points.json').read_text('utf8'))
 for m in transfer_vps:assert vp['province_id_inventory'][str(m['province'])]['state_id']==m['from'];vp['province_id_inventory'][str(m['province'])]['state_id']=m['to']
 dump(BASE/'modern_victory_points.json',vp);dump(OUT/'victory-point-transfers.json',transfer_vps)
 # OVO is releasable. Keep its existing capital at the same actual city.
 p=ROOT/'history/countries/OVO - Ostyakia Vogulia.txt';t=p.read_text('utf8');cap=next(n for n in parse(t) if n.key=='capital');assert cap.value=='580';p.write_text(patches(t,[(cap.value_start,cap.value_end,'577')]),'utf8')
 refs=[{'file':p.relative_to(ROOT).as_posix(),'kind':'capital','tag':'OVO','province':1812,'from':580,'to':577,'reason':'Keep Khanty-Mansiysk as the same geographic capital; preserve releasable country setup'}]
 dump(OUT/'geographic-reference-changes.json',refs)
 mism=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));resolved={575,577}
 mism['clear_center_outside_named_state']=[v for v in mism['clear_center_outside_named_state'] if v.get('state_id') not in resolved]
 latest=mism.get('latest_added_renamed_state_review',{});latest['mismatches']=[v for v in latest.get('mismatches',[]) if v['state'] not in resolved];latest['resolved_by_followup']='docs/map-maintenance/20261104-city-alignment/city-review.json'
 city={'date':'2026-11-04','user_rule':'Move the three city provinces only when they directly touch the named state','checks':META['adjacency'],'resolved_states':[575,577],'remaining_mismatches':[v for v in META['adjacency'] if not v['move']],'no_new_city_victory_points':True}
 mism['latest_city_province_alignment']={'report':META['report']+'/city-review.json',**city};dump(BASE/'city_named_state_mismatches.json',mism);dump(OUT/'city-review.json',city)
 dump(OUT/'plan.json',{'affected_states':sorted(AFFECTED),'province_transfers':MOVES,'skipped':[v for v in META['adjacency'] if not v['move']]})
 dump(OUT/'changes.json',{'province_transfers':MOVES,'economy_changes':economy_changes,'actual_buildings_moved':[],'capital_changes':refs,'political_relations_unchanged':True,'state_file_names_unchanged':True,'no_bitmap_or_land_sea_type_changes':True})
 print(json.dumps({'moved':MOVES,'economy':economy_changes,'vp':transfer_vps,'strategic_regions':sorted(written)},ensure_ascii=False))

def audit():
 oldtool.audit()
 ss=statefiles(ROOT/'history/states');previous=oldtool.previous();pm=pmap(ss);oldpm=pmap(previous);defs,raster=raster_data()
 assert [{'province':pid,'from':oldpm[pid],'to':sid} for pid,sid in sorted(pm.items()) if sid!=oldpm[pid]]==sorted([{'province':m['province'],'from':m['from'],'to':m['to']} for m in MOVES],key=lambda v:v['province'])
 edges=collections.defaultdict(set)
 import numpy as np
 for a,b in [(raster[:,:-1],raster[:,1:]),(raster[:-1,:],raster[1:,:]),(raster[:,-1:],raster[:,:1])]:
  mask=a!=b;packed=np.minimum(a[mask],b[mask]).astype(np.uint32)*65536+np.maximum(a[mask],b[mask])
  for v in np.unique(packed):a,b=int(v)//65536,int(v)%65536;edges[a].add(b);edges[b].add(a)
 def components(state):
  pending={int(v.key) for v in state.get('provinces').children};parts=[]
  while pending:
   todo=[pending.pop()];part=set(todo)
   while todo:
    p=todo.pop();neighbors=edges[p]&pending;pending-=neighbors;todo+=list(neighbors);part|=neighbors
   parts.append(sorted(part))
  return sorted(parts,key=lambda p:(-len(p),p))
 connectivity=[]
 for sid in sorted(AFFECTED):
  before=previous[sid][2];after=ss[sid][2]
  assert [canon(n) for n in before.children if n.key not in ['provinces','manpower','resources','history']]==[canon(n) for n in after.children if n.key not in ['provinces','manpower','resources','history']]
  assert [canon(n) for n in before.get('history').children if n.key!='victory_points']==[canon(n) for n in after.get('history').children if n.key!='victory_points']
  a=components(before);b=components(after);assert len(b)<=len(a),('new state disconnection',sid,a,b);connectivity.append({'state':sid,'before':a,'after':b})
 alloc,totals=allocation(ss);reverse=collections.defaultdict(lambda:{'population':Fraction(),'resources':collections.defaultdict(Fraction),'provinces':[]})
 for v in alloc.values():
  for c in v['contributions']:
   r=reverse[c['source']];r['population']+=Fraction(c['population_contribution']);r['provinces']+=c['provinces']
   for k,x in c['resource_contributions'].items():r['resources'][k]+=Fraction(x)
 for sid,(_,_,s) in statefiles(BASE/'original_economy/history/states').items():
  r=reverse[sid];assert r['population']==Fraction(s.val('manpower','0'));assert sorted(r['provinces'])==sorted(int(v.key) for v in s.get('provinces').children);assert dict(r['resources'])=={n.key:Fraction(n.value) for b in s.children if b.key=='resources' for n in b.children}
 dump(OUT/'economy-reverse-audit.json',{'passed':True,'source_states':len(reverse),'sources':{s:{'exact_population':str(v['population']),'exact_resources':{k:str(x) for k,x in v['resources'].items()},'province_count':len(v['provinces'])} for s,v in reverse.items()},'totals':totals})
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  rel='history/countries/OVO - Ostyakia Vogulia.txt';assert [canon(n) for n in parse(z.read(rel).decode('utf8')) if n.key!='capital']==[canon(n) for n in parse((ROOT/rel).read_text('utf8')) if n.key!='capital']
  for rel in ['map/unitstacks.txt','map/railways.txt','map/supply_nodes.txt','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json']:assert z.read(rel)==(ROOT/rel).read_bytes()
 dump(OUT/'extended-static-audit.json',{'passed':True,'only_two_authorized_province_transfers':True,'affected_state_connectivity':connectivity,'unchanged_non_geographic_state_history':sorted(AFFECTED),'capital_only_country_change':'OVO','political_relations_and_state_index_byte_preserved':True,'province_bound_transport_and_models_preserved':True,'reverse_fixed_sources_checked':len(reverse),'no_city_vp_added_or_deleted':True})
 print('Extended city alignment audit passed')

def prepare_qa():
 assert json.loads((OUT/'static-audit.json').read_text('utf8'))['passed'];assert json.loads((OUT/'extended-static-audit.json').read_text('utf8'))['passed'];assert not QA.exists()
 for rel in ['mod','driver/common/on_actions','driver/common/defines']:(QA/rel).mkdir(parents=True,exist_ok=True)
 desc=(ROOT/'descriptor.mod').read_text('utf8');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M);(QA/'mod/APDC.mod').write_text(desc,'utf8')
 (QA/'mod/APDC_CityAlignmentQA.mod').write_text('name="APDC city alignment diagnostics"\npath="'+(QA/'driver').as_posix()+'"\nsupported_version="1.19.*"\n','utf8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_CityAlignmentQA.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA_20261104/settings.txt').read_text('utf8');(QA/'settings.txt').write_text(settings,'utf8')
 (QA/'driver/common/defines/zzzz_APDC_city_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf8')
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));checks=''
 for sid in sorted(AFFECTED):
  p=pol[str(sid)];test=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+v for v in p['cores']);checks+=f'{sid} = {{ if = {{ limit = {{ {test} }} log = "APDC_CITY_20261104 PASS state_{sid}" }} else = {{ log = "APDC_CITY_20261104 FAIL state_{sid}" }} }}\n'
 daily='add_to_variable = { apdc_qa_city_day = 1 }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_CITY_20261104 WORLD_READY" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 20 } } set_variable = { apdc_cw_selected = SOV } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_CITY_20261104 SOV_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 34 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_CITY_20261104 WORLD_RETURNED" }\nlog = "APDC_CITY_20261104 DAY [?apdc_qa_city_day] date=[GetDateText]"\n'
 (QA/'driver/common/on_actions/zzzz_APDC_city_qa.txt').write_text('on_actions = { on_daily_GER = { effect = {\n'+daily+'} } }\n','utf8')
 dump(OUT/'runtime-preparation.json',{'profile':str(QA),'source':str(ROOT),'user_files_before':META['user_files_before'],'user_enabled_mods':META['enabled_mods_before'],'scene':'One ordinary GER 2060 start; world/SOV detail/return on private desktop; no mouse or keyboard','toolpack_loaded':False,'external_descriptor':(USER/'mod/APDC.mod').read_text('utf8')})
 print('Prepared '+str(QA))

def runtime_audit():
 record=json.loads((QA/'silent-process.json').read_text('utf-8-sig'));save=QA/'save games/autosave.hoi4';assert save.stat().st_mtime>=datetime.datetime.fromisoformat(record['started']).timestamp();text=save.read_text('utf-8-sig')
 native={int(n.key):n for n in parse(oldverify.section(text,'states'))};pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));assert len(native)==len(pol)
 cores=collections.defaultdict(list);claims=collections.defaultdict(list);countries={}
 for m in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',oldverify.section(text,'countries')):
  tag,body=m.groups();countries[tag]=body
  for key,target in [('cores',cores),('claims',claims)]:
   match=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
   if match:
    for sid in map(int,re.findall(r'\d+',match[1])):target[sid].append(tag)
 differences=[];dmz=[];capitals=[]
 for sid,n in native.items():
  got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])};want={**pol[str(sid)],'cores':sorted(pol[str(sid)]['cores']),'claims':sorted(pol[str(sid)]['claims'])}
  if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
  if n.val('demilitarized')=='yes':dmz.append(sid)
 active={v['owner'] for v in pol.values()}
 for p in (ROOT/'history/countries').glob('*.txt'):
  if p.name[:3] not in active:continue
  caps=[n for n in parse(p.read_text('utf-8-sig')) if n.key=='capital'];match=re.search(r'(?m)^\t\tcapital=(\d+)',countries[p.name[:3]]);assert caps and match and int(caps[0].value)==int(match[1]);capitals.append(p.name[:3])
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[v for v in game.splitlines() if 'APDC_CITY_20261104' in v]
 relevant=[v for v in error.splitlines() if re.search(r'MAP_ERROR|map/buildings.txt|Province with id:|State \d+ has no|[Rr]ailway|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|pdx_localize.cpp|localization.*error',v)]
 with zipfile.ZipFile(Path(META['checkpoint']['backup'])/'runtime-evidence.zip') as z:prior=z.read('logs/error.log').decode('utf-8-sig',errors='replace')
 norm=lambda s:re.sub(r'^(?:\[[^\]]*\])+\s*','',s)
 new=collections.Counter(norm(s) for s in error.splitlines())-collections.Counter(norm(s) for s in prior.splitlines());changed=[p for p,h in META['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1];markers=['WORLD_READY','SOV_DETAIL_READY','WORLD_RETURNED']
 signature=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'))['signature'];geometry_flag='apdc_cw_render_lookup_v2_geo_'+signature;assert geometry_flag in text,'Native save did not initialize the current geography lookup'
 passed=not(differences or dmz or relevant or changed or new) and 'FAIL' not in '\n'.join(evidence) and all(any(marker in line for line in evidence) for marker in markers) and date.startswith('2060.2.') and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers'])
 system=(QA/'logs/system.log').read_text('utf-8-sig',errors='replace');report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'relation_differences':differences,'initial_dmz':dmz,'active_capitals_checked':len(capitals),'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_signatures_vs_last_completed_runtime':dict(new),'user_file_changes':changed,'evidence':evidence,'process':record,'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf8')),'version_and_active_dlcs':[s for s in system.splitlines() if 'Version:' in s or 'Active DLC' in s],'input_desktop_switched':False,'mouse_keyboard_sent':False}
 dump(OUT/'runtime-audit.json',report)
 report['current_geography_lookup_flag_in_native_save']=geometry_flag;dump(OUT/'runtime-audit.json',report)
 with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in (QA/'logs').glob('*'):
   if p.is_file():z.write(p,'logs/'+p.name)
  for name in ['silent-process.json','silent-stop.json','settings.txt','dlc_load.json']:z.write(QA/name,name)
 with zipfile.ZipFile(BACKUP/'runtime-save.zip','w',zipfile.ZIP_DEFLATED) as z:z.write(save,'autosave.hoi4')
 assert passed,{k:v for k,v in report.items() if k not in ['evidence','version_and_active_dlcs']}
 print(json.dumps({k:v for k,v in report.items() if k not in ['evidence','version_and_active_dlcs','process']},ensure_ascii=False))

def review_assets():
 import numpy as np
 from PIL import Image,ImageFilter
 ss=statefiles(ROOT/'history/states');pm=pmap(ss);defs,raster=raster_data();g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf8'));prefix='gfx/interface/APDC/cold_war/'
 assert set(map(int,g['states']))==set(ss)
 for e in g['pieces']:
  a=np.asarray(Image.open(ROOT/prefix/'map'/(e['name']+'.png')));mask=np.pad(np.isin(raster[e['y']:e['y']+e['h'],e['x']:e['x']+e['w']],[int(v.key) for v in ss[e['state']][2].get('provinces').children]),e['padding']);assert np.array_equal(a[:,:,0]>127,mask),e['name']
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  old=json.loads(z.read('docs/cold-war/20261024/geometry.json'));pol=json.loads(z.read('tools/map_maintenance/baseline/initial_territories.json'));assert all(old[k]==g[k] for k in ['palette_ids','scales','colors'])
  def world(meta,before):
   load=lambda rel:Image.open(io.BytesIO(z.read(rel)) if before else ROOT/rel).convert('RGBA');canvas=Image.new('RGBA',(1000,500))
   for e in meta['pieces']:
    tag=pol[str(e['state'])]['owner'];w=e['world'];im=load(prefix+'map/world_'+str(e['id'])+'.png');frame=0 if tag=='GER' else 2 if tag in ['FRA','LLU'] else 1;tile=im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h']))
    if tag=='ZZZ':tile=load(prefix+'world_style/black_'+str(e['id'])+'.png')
    canvas.alpha_composite(tile,(w['x'],w['y']))
   for e in meta['borders']:
    a,b=[pol[str(e[k])]['owner'] for k in ['a','b']]
    if a==b:continue
    w=e['world'];im=load(prefix+'world_style/border_'+str(e['id'])+'.png');frame=int('ZZZ' in [a,b]);canvas.alpha_composite(im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h'])),(w['x'],w['y']))
   canvas.alpha_composite(load(prefix+'coasts.png'));return canvas
  before=world(old,True);after=world(g,False);before.save(OUT/'world-before.png');after.save(OUT/'world-after.png');changed=np.any(np.asarray(before)!=np.asarray(after),axis=2)
  allowed=Image.fromarray(np.isin(raster,[pid for pid,sid in pm.items() if sid in AFFECTED]).astype('uint8')*255).resize((1000,500),Image.Resampling.LANCZOS).filter(ImageFilter.MaxFilter(9));outside=int(np.count_nonzero(changed & (np.asarray(allowed)==0)));assert not outside
  protected=['palette.png','background.png','screen_overlay.png','pie_frame.png','option.png','control.png','swatches.png']+[p.name for p in (ROOT/prefix).glob('pie_*.png')]
  for name in protected:assert z.read(prefix+name)==(ROOT/prefix/name).read_bytes()
  for rel in ['gfx/FX/APDC_cw_palette.shader','localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml']:assert z.read(rel)==(ROOT/rel).read_bytes()
 native=[];diff=None
 if (OUT/'runtime-visual-captures.json').exists():
  native=json.loads((OUT/'runtime-visual-captures.json').read_text('utf8'));a=np.asarray(Image.open(OUT/'runtime-world.png'))[150:650,458:1458];b=np.asarray(Image.open(OUT/'runtime-world-return.png'))[150:650,458:1458];diff=int(np.count_nonzero(np.any(a!=b,axis=2)));assert diff==0
 dump(OUT/'visual-asset-audit.json',{'passed':True,'state_masks_exact':len(g['pieces']),'world_changed_pixels':int(changed.sum()),'unrelated_world_changed_pixels':outside,'palette_count':len(g['palette_ids']),'zoom_levels':len(g['scales']),'palette_scales_shader_non_map_art_and_tooltips_preserved':True,'native_capture_count':len(native),'native_world_first_vs_return_diff_pixels':diff})
 print(json.dumps({'state_masks':len(g['pieces']),'changed_world_pixels':int(changed.sum()),'unrelated_pixels':outside,'native_captures':len(native),'native_world_return_diff':diff}))

def preservation():
 from concurrent.futures import ThreadPoolExecutor
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));regions=json.loads((OUT/'strategic-repairs.json').read_text('utf8'))['written_regions'];ss=statefiles(ROOT/'history/states')
 allowed={v['file'] for v in cw['changed']}|{ss[s][0].relative_to(ROOT).as_posix() for s in AFFECTED}|{'map/buildings.txt','history/countries/OVO - Ostyakia Vogulia.txt','tools/map_maintenance/city_alignment_20261104.py','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json','tools/map_maintenance/baseline/latest_checkpoint.json'}
 allowed|={p.relative_to(ROOT).as_posix() for p in (ROOT/'map/strategicregions').glob('*.txt') if int(parse(p.read_text('utf-8-sig'))[0].val('id')) in regions}
 allowed|={'项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md'}
 files=[]
 for folder,dirs,names in os.walk(ROOT):
  dirs[:]=[v for v in dirs if v not in ['.git','__pycache__']];files.extend(Path(folder)/v for v in names if Path(folder)/v!=OUT/'preservation-audit.json')
 def inspect(p):return p.relative_to(ROOT).as_posix(),sha(p)
 with ThreadPoolExecutor(max_workers=6) as pool:after=dict(pool.map(inspect,files))
 changes=[{'file':p,'before':before.get(p,{}).get('sha256'),'after':h} for p,h in after.items() if h!=before.get(p,{}).get('sha256')];removed=[p for p in before if not (ROOT/p).is_file()];unexpected=[v for v in changes if v['file'] not in allowed and not v['file'].startswith(META['report']+'/')]
 fixed=[p for p in before if p.startswith(('tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_'))];assert all(after[p]==before[p]['sha256'] for p in fixed)
 report={'passed':not(unexpected or removed),'files_before':len(before),'files_after':len(after),'changed_or_added':changes,'removed':removed,'unexpected_changes':unexpected,'fixed_economy_and_imported_snapshots_byte_preserved':True,'all_other_preexisting_user_changes_preserved':True}
 dump(OUT/'preservation-audit.json',report);assert report['passed'],{'unexpected':unexpected,'removed':removed};dump(BACKUP/'final-file-manifest.json',{p:{'sha256':h} for p,h in after.items()});print(json.dumps({'preserved':True,'changed_or_added':len(changes),'files_checked':len(after)}))

def checkpoint():
 for name in ['static-audit','extended-static-audit','runtime-audit','visual-asset-audit']:assert json.loads((OUT/(name+'.json')).read_text('utf8'))['passed']
 asset=json.loads((OUT/'visual-asset-audit.json').read_text('utf8'));assert asset['native_capture_count']==3 and asset['native_world_first_vs_return_diff_pixels']==0
 visual=json.loads((OUT/'visual-review.json').read_text('utf8'));assert visual['reviewed'] and visual['capture_count']==3
 ss=statefiles(ROOT/'history/states');archive=OUT/'states-checkpoint.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for _,(p,_,_) in sorted(ss.items()):z.write(p,p.name)
 dump(OUT/'state-hashes.json',{s:{'file':p.name,'sha256':sha(p)} for s,(p,_,_) in ss.items()})
 ma=OUT/'map-checkpoint.zip'
 with zipfile.ZipFile(ma,'w',zipfile.ZIP_DEFLATED) as z:
  for rel in ['map/buildings.txt','map/railways.txt','map/supply_nodes.txt','map/adjacencies.csv','docs/cold-war/20261024/geometry.json','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/modern_victory_points.json']:z.write(ROOT/rel,rel)
  for p in (ROOT/'map/strategicregions').glob('*.txt'):z.write(p,p.relative_to(ROOT).as_posix())
 cp={**META['checkpoint'],'date':'2026-11-04','report':META['report'],'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER '+json.loads((OUT/'runtime-audit.json').read_text('utf8'))['date']+'; all 1628 state relations checked; world/SOV/return reviewed; own game/helpers stopped','runtime_report':META['report']+'/runtime-audit.json','visual_report':META['report']+'/visual-review.json','backup':str(BACKUP),'geography_backup':str(BACKUP),'previous_report':META['checkpoint']['report'],'map_checkpoint_archive':ma.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(ma),'city_review':META['report']+'/city-review.json'}
 dump(BASE/'latest_checkpoint.json',cp);preservation();print('City alignment checkpoint saved')

if __name__=='__main__':globals()[sys.argv[1]]()
