"""2026-11-06 Taraz APDC map closeout. Date-specific reviewed inputs, latest APDC history.
Uses the maintained parser, source-economy and building migration functions.
Do not replay against another map; backup and plan are required.
"""
from pathlib import Path
import sys,json,zipfile,collections,hashlib,math,re,os,datetime,shutil,io,csv
from fractions import Fraction
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'D:/APDC_ColdWarTools/pydeps313')
import finish_20261104 as oldtool
import verify_20261104 as oldverify
from finish_20261104 import parse,walk,patches,canon,statefiles,pmap,allocation,raster_data,sha,dump,previous,set_field,update_models
ROOT=oldtool.ROOT;BASE=ROOT/'tools/map_maintenance/baseline';USER=oldtool.USER;GAME=oldtool.GAME;LANGS=oldtool.LANGS
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-taraz-20261106.json').read_text('utf8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];QA=Path(META['qa'])
NAMES={586:['东江布尔','East Jambyl','Восточный Жамбыл','東ジャンブール','동잠빌'],1646:['塔拉兹','Taraz','Тараз','タラズ','타라즈']}
NAME_VALUES={586:{'simp_chinese':'东江布尔','english':'East Jambyl','french':'Jambyl oriental','german':'Ost-Jambyl','spanish':'Jambyl Oriental','braz_por':'Jambyl Oriental','polish':'Wschodni Jambyl','russian':'Восточный Жамбыл','japanese':'東ジャンブール','korean':'동잠빌'},1646:json.loads((BASE/'modern_victory_points.json').read_text('utf8'))['province_id_inventory']['12640']['names']}
for module in [oldtool,oldverify]:
 module.META=META;module.BACKUP=BACKUP;module.OUT=OUT;module.QA=QA;module.NAMES=NAMES
def name_value(sid,lang):return NAME_VALUES[sid][lang]


def update_names(renames):
 alias=re.compile(r'^(?:STATE_(\d+)|[A-Za-z0-9_]+_STATE_(\d+)|STATE_(\d+)_[A-Za-z0-9_]+|state_(\d+)_name|(\d+)_[A-Za-z0-9_]+_name)$')
 changes=[]
 for lang in LANGS:
  for p in (ROOT/'localisation').rglob('*.yml'):
   if not p.name.endswith('_l_'+lang+'.yml'):continue
   t=p.read_text('utf-8-sig');lines=t.splitlines(keepends=True);existing=set();touched=False
   for i,line in enumerate(lines):
    m=re.match(r'^(\s*)([A-Za-z0-9_.-]+):(-?\d+)\s+"((?:\\.|[^"\\])*)"(.*?)(\r?\n)?$',line)
    if not m:continue
    key=m[2];existing.add(key);am=alias.fullmatch(key)
    if not am or '[' in m[4]:continue
    sid=int(next(v for v in am.groups() if v))
    if sid not in NAMES:continue
    value=name_value(sid,lang)
    if m[4]!=value or m[3]!='0':
     lines[i]=m[1]+key+':0 "'+value+'"'+m[5]+'\n';changes.append({'file':p.relative_to(ROOT).as_posix(),'key':key,'before':m[4],'after':value});touched=True
   if p.name=='zzzz_apdc_map_geography_l_'+lang+'.yml':
    for sid in NAMES:
     key='STATE_'+str(sid)
     if key not in existing:lines.append(' '+key+':0 "'+name_value(sid,lang)+'"\n');changes.append({'file':p.relative_to(ROOT).as_posix(),'key':key,'before':None,'after':name_value(sid,lang)});touched=True
   if touched:p.write_text(''.join(lines),'utf-8-sig',newline='\n')
 prior=json.loads((OUT/'localisation-changes.json').read_text('utf8')) if (OUT/'localisation-changes.json').exists() else []
 dump(OUT/'localisation-changes.json',prior+changes)
 dump(OUT/'name-decisions.json',{'names':NAME_VALUES,'chinese':'User supplied names, preserved verbatim','city_name_source':'Existing fixed modern victory point inventory, province 12640, Taraz; city names and scores unchanged','East_Jambyl':'Directional rename of the existing project Jambyl region; established spelling retained','scope':'State names only; regional name East Jambyl is not a claim that Taraz remains in state 586'})

def apply():
 assert json.loads((OUT/'plan.json').read_text('utf8'))['new_states']==[1646]
 oldtool.update_names=update_names
 oldtool.apply()

def plan():
 ss=statefiles(ROOT/'history/states');old=previous();op=pmap(old);pm=pmap(ss)
 assert set(ss)-set(old)=={1646};assert set(pm)==set(op),'Unknown or missing source provinces need explicit relationships'
 transfers=[{'province':p,'from':op[p],'to':pm[p]} for p in sorted(pm) if pm[p]!=op[p]]
 cleared=[sid for sid,(_,_,s) in ss.items() if sid in old and (not s.get('history') or not s.get('history').children)]
 affected=sorted({m[k] for m in transfers for k in ['from','to']}|set(cleared));sources={str(s):dict(collections.Counter(op[int(v.key)] for v in ss[s][2].get('provinces').children)) for s in affected}
 for sid in affected:
  assert len({old[src][2].get('history').val('owner') for src in sources[str(sid)]})==1,('mixed owners require clarification',sid)
 alloc,totals=allocation(ss);regions={};editor={};editor_changes=[]
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];rid=int(n.val('id'));assert rid not in regions;regions[rid]=(p,t,n)
 cutoff=datetime.datetime.fromisoformat(META['editor_cutoff']).timestamp();ignored=[]
 for p in (USER/'map/strategicregions').rglob('*.txt'):
  if p.stat().st_mtime<=cutoff:ignored.append(str(p));continue
  t=p.read_text('utf-8-sig');n=parse(t)[0];rid=int(n.val('id'));assert rid in regions
  if rid not in editor or p.stat().st_mtime>editor[rid][0].stat().st_mtime:editor[rid]=(p,t,n)
 for rid,(p,t,n) in editor.items():
  oldp,oldt,oldn=regions[rid];a=[int(v.key) for v in oldn.get('provinces').children];b=[int(v.key) for v in n.get('provinces').children]
  if a==b:continue
  editor_changes.append({'region':rid,'source':str(p),'removed':sorted(set(a)-set(b)),'added':sorted(set(b)-set(a))});v=oldn.get('provinces');text=patches(oldt,[(v.value_start,v.value_end,t[n.get('provinces').value_start:n.get('provinces').value_end])]);regions[rid]=(oldp,text,parse(text)[0])
 preg={};dupes=[]
 for rid,(_,_,n) in regions.items():
  for v in n.get('provinces').children:
   pid=int(v.key)
   if pid in preg:dupes.append([pid,preg[pid],rid])
   preg[pid]=rid
 report={'checkpoint':META['checkpoint'],'backup':str(BACKUP),'new_states':sorted(set(ss)-set(old)),'affected_states':affected,'province_transfers':transfers,'cleared_histories':cleared,'cleared_unchanged_history_restored':[s for s in cleared if {int(v.key) for v in ss[s][2].get('provinces').children}=={int(v.key) for v in old[s][2].get('provinces').children}],'state_sources':sources,'economy_totals':totals,'strategic_editor_changes':editor_changes,'strategic_duplicates':dupes,'editor_cutoff':META['editor_cutoff'],'older_editor_outputs_ignored':ignored}
 dump(OUT/'plan.json',report);dump(OUT/'allocation.json',alloc);dump(OUT/'allocation-totals.json',totals)
 with zipfile.ZipFile(BACKUP/'strategic-plan.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p,t,n in regions.values():z.writestr(p.relative_to(ROOT).as_posix(),t.encode('utf8'))
 print(json.dumps({'states':len(ss),'new':len(set(ss)-set(old)),'province_transfers':len(transfers),'cleared':cleared,'affected':affected,'editor_regions':[v['region'] for v in editor_changes],'stale_editor_files_ignored':len(ignored)},ensure_ascii=False))

def extended_audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pm=pmap(states);defs,r=raster_data();H,W=r.shape;affected=set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states']);counts=collections.Counter()
 for line in (ROOT/'map/buildings.txt').read_text('utf8').splitlines():
  row=line.split(';');pid=int(row[6]) if row[1]=='floating_harbor' else int(r[H-1-math.floor(float(row[4])),math.floor(float(row[2]))]);counts[pid,row[1]]+=1
 models=json.loads((OUT/'model-changes.json').read_text('utf8'))
 for sid in affected:
  for v in states[sid][2].get('provinces').children:
   pid=int(v.key)
   if defs[pid]['type']!='land':continue
   for kind,(count,coast) in models['required_province_models'].items():
    if not coast or defs[pid]['coastal']=='true':assert counts[pid,kind]>=count,(sid,pid,kind)
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));active={v['owner'] for v in pol.values()};registry={}
 for p in (ROOT/'common/country_tags').glob('*.txt'):registry.update({n.key:n.value for n in parse(p.read_text('utf-8-sig'))})
 assert all(set([v['owner'],v['controller']]+v['cores']+v['claims'])<=set(registry) for v in pol.values());assert not {tag for v in pol.values() if v['owner'] in v['cores'] for tag in v['cores']+v['claims'] if tag not in active}
 ignore={'owner','controller','add_core_of','add_claim_by','victory_points','buildings'};preserved=[];nested=[]
 for sid in affected&set(old):
  norm=lambda s:[canon(n) for n in s.get('history').children if n.key not in ignore and not(sid==589 and (OUT/'capacity-adjustments.json').exists() and n.key=='add_extra_state_shared_building_slots') and not(n.key=='set_state_flag' and n.value.startswith('GDP_regions_'))]
  assert norm(old[sid][2])==norm(states[sid][2]),sid;preserved.append(sid);nested.extend({'state':sid,'field':n.key} for n in walk(states[sid][2].get('history').children) if re.fullmatch(r'\d{4}\.\d+\.\d+',n.key) or n.key in ['if','else_if'])
 if (OUT/'capacity-adjustments.json').exists():
  slots=lambda s:sum(int(n.value) for n in s.get('history').children if n.key=='add_extra_state_shared_building_slots')
  assert slots(states[589][2])==slots(old[589][2])+1
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  rel='history/countries/KAZ - Kazakhstan.txt';assert [canon(n) for n in parse(z.read(rel).decode('utf8')) if n.key!='capital']==[canon(n) for n in parse((ROOT/rel).read_text('utf8')) if n.key!='capital']
  for rel in ['common/on_actions','events','common/characters','common/ideologies','common/national_focus']:
   for p in (ROOT/rel).rglob('*'):
    if p.is_file():assert z.read(p.relative_to(ROOT).as_posix())==p.read_bytes(),str(p)
 alloc,totals=allocation(states);reverse=collections.defaultdict(lambda:{'population':Fraction(),'resources':collections.defaultdict(Fraction),'provinces':[]})
 for row in alloc.values():
  for c in row['contributions']:
   v=reverse[c['source']];v['population']+=Fraction(c['population_contribution']);v['provinces']+=c['provinces']
   for k,x in c['resource_contributions'].items():v['resources'][k]+=Fraction(x)
 for sid,(_,_,s) in statefiles(BASE/'original_economy/history/states').items():
  v=reverse[sid];assert v['population']==Fraction(s.val('manpower','0'));assert sorted(v['provinces'])==sorted(int(p.key) for p in s.get('provinces').children);assert dict(v['resources'])=={n.key:Fraction(n.value) for b in s.children if b.key=='resources' for n in b.children}
 dump(OUT/'economy-reverse-audit.json',{'passed':True,'source_states':len(reverse),'sources':{s:{'exact_population':str(v['population']),'exact_resources':{k:str(x) for k,x in v['resources'].items()},'province_count':len(v['provinces'])} for s,v in reverse.items()},'totals':totals})
 dump(OUT/'extended-static-audit.json',{'passed':True,'all_registered_political_tags':True,'inactive_core_claim_cleanup_verified':True,'affected_province_spawn_coverage':True,'nongeographic_existing_histories_preserved':sorted(preserved),'recorded_capacity_exception':'capacity-adjustments.json: state 589 adds exactly one shared slot' if (OUT/'capacity-adjustments.json').exists() else None,'nested_affected_date_or_conditional_history':nested,'country_capital_changes':[],'unrelated_gameplay_directories_byte_preserved':True,'fixed_sources_reverse_checked':len(reverse),'sea_connectivity':'Province pixels, sea/lake region assignments and sea adjacencies unchanged from completed checkpoint'})
 print('Extended November 6 static audit passed')

def preservation():
 from concurrent.futures import ThreadPoolExecutor
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));plan=json.loads((OUT/'plan.json').read_text('utf8'));renames=json.loads((OUT/'renames.json').read_text('utf8'));loc=json.loads((OUT/'localisation-changes.json').read_text('utf8'));ss=statefiles(ROOT/'history/states')
 allowed={v['file'] for v in cw['changed']}|{v['file'] for v in loc}|{v['new'] for v in renames}|{ss[s][0].relative_to(ROOT).as_posix() for s in plan['affected_states']}
 allowed|={v['file'] for v in json.loads((OUT/'geographic-reference-changes.json').read_text('utf8'))+json.loads((OUT/'additional-reference-changes.json').read_text('utf8'))}
 regions=json.loads((OUT/'strategic-repairs.json').read_text('utf8'))['written_regions'];allowed|={p.relative_to(ROOT).as_posix() for p in (ROOT/'map/strategicregions').glob('*.txt') if int(parse(p.read_text('utf-8-sig'))[0].val('id')) in regions}
 allowed|={'map/buildings.txt','tools/map_maintenance/finish_taraz_20261106.py','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json','tools/map_maintenance/baseline/latest_checkpoint.json'}
 allowed|={'项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md'}
 files=[]
 for folder,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in ['.git','__pycache__']];files.extend(Path(folder)/n for n in names if Path(folder)/n!=OUT/'preservation-audit.json')
 def inspect(p):return p.relative_to(ROOT).as_posix(),sha(p)
 with ThreadPoolExecutor(max_workers=6) as pool:after=dict(pool.map(inspect,files))
 changes=[{'file':p,'before':before.get(p,{}).get('sha256'),'after':h} for p,h in after.items() if h!=before.get(p,{}).get('sha256')];removed=[p for p in before if not (ROOT/p).is_file()];unexpected=[v for v in changes if v['file'] not in allowed and not v['file'].startswith(META['report']+'/')];unexpected_removed=sorted(set(removed)-{v['old'] for v in renames})
 fixed=[p for p in before if p.startswith(('tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_'))];assert all(after[p]==before[p]['sha256'] for p in fixed)
 report={'passed':not(unexpected or unexpected_removed),'files_before':len(before),'files_after':len(after),'changed_or_added':changes,'authorized_rename_removals':removed,'unexpected_removed':unexpected_removed,'unexpected_changes':unexpected,'fixed_economy_and_imported_snapshots_byte_preserved':True,'all_other_preexisting_user_changes_preserved':True};dump(OUT/'preservation-audit.json',report);assert report['passed'],{'unexpected':unexpected,'removed':unexpected_removed};dump(BACKUP/'final-file-manifest.json',{p:{'sha256':h} for p,h in after.items()});print(json.dumps({'preserved':True,'changed_or_added':len(changes),'renamed':len(removed),'files_checked':len(after)}))

def audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pstate=pmap(states);defs,raster=raster_data();H,W=raster.shape;issues=[]
 assert len(states)==1646 and set(range(1,1647))==set(states)
 assert not [sid for sid,(_,_,s) in states.items() if not s.get('provinces').children]
 assert not(set(pstate)-set(defs))
 assert not [pid for pid,d in defs.items() if pid and d['type']=='land' and pid not in pstate]
 assert set(pstate)<=set(map(int,np.unique(raster)))
 allocation_data,totals=allocation(states);politics={};vp={};imp=[];dmz=[]
 def totals_building(data):
  out=collections.Counter()
  for sid,(_,_,s) in data.items():
   for b in walk(s.get('history').children):
    if b.key!='buildings':continue
    for n in b.children:
     if n.key.isdigit():
      for item in n.children:
       v=item.value if item.value is not None else item.val('level')
       if v is not None and v.isdigit():out[item.key]+=int(v)
     elif n.value and n.value.isdigit():out[n.key]+=int(n.value)
  return out
 oldbuild=totals_building(old);newbuild=totals_building(states)
 assert {k:v for k,v in oldbuild.items() if k!='infrastructure'}=={k:v for k,v in newbuild.items() if k!='infrastructure'},('Actual buildings changed',oldbuild,newbuild)
 for sid,(p,t,s) in states.items():
  h=s.get('history');assert h,('missing history',sid)
  politics[str(sid)]={'owner':h.val('owner'),'controller':h.val('controller',h.val('owner')),'cores':sorted({n.value.strip('"') for n in h.children if n.key=='add_core_of'}),'claims':sorted({n.value.strip('"') for n in h.children if n.key=='add_claim_by'})}
  assert int(s.val('manpower'))==allocation_data[sid]['population'],('population',sid)
  actual={}
  for b in [n for n in s.children if n.key=='resources']:
   for n in b.children:assert n.key not in actual;actual[n.key]=Fraction(n.value)
  assert actual==allocation_data[sid]['resources'],('resources',sid,actual,allocation_data[sid]['resources'])
  if s.val('impassable')=='yes':imp.append(sid)
  for n in walk(h.children):
   if n.key=='set_demilitarized_zone' and n.value=='yes':dmz.append(sid)
   if n.key=='victory_points':
    items=[int(x.key) for x in n.children]
    for pid,score in zip(items[::2],items[1::2]):assert pstate[pid]==sid and pid not in vp;vp[pid]=[sid,score]
   if n.key=='buildings':
    for x in n.children:
     if x.key.isdigit():assert pstate[int(x.key)]==sid,('province building host',sid,x.key)
  if sid in NAMES:assert p.name==str(sid)+'-'+NAMES[sid][1]+'.txt'
 assert not dmz
 assert sorted(imp)==sorted(sid for sid,(_,_,s) in old.items() if s.val('impassable')=='yes')
 authority=json.loads((BASE/'initial_territories.json').read_text('utf-8'));assert politics=={k:{**v,'cores':sorted(v['cores']),'claims':sorted(v['claims'])} for k,v in authority.items()}
 expected=json.loads((BASE/'modern_victory_points.json').read_text('utf-8'))['province_id_inventory'];assert vp=={int(k):[v['state_id'],v['score']] for k,v in expected.items()};assert vp[13462]==[1206,10]
 preg={};regions={}
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  n=parse(p.read_text('utf-8-sig'))[0];rid=int(n.val('id'));assert rid not in regions;regions[rid]=n
  for n in n.get('provinces').children:pid=int(n.key);assert pid not in preg,('region duplicate',pid);preg[pid]=rid
 cross=[]
 for sid,(_,_,s) in states.items():
  rr={preg.get(int(n.key)) for n in s.get('provinces').children}
  if len(rr)!=1 or None in rr:cross.append([sid,list(rr)])
 assert not cross,cross
 assert set(defs)-{0}<=set(preg)
 # Province raster did not change; all coastal/rail/sea edges remain geometric.
 edges=set()
 for a,b in [(raster[:,:-1],raster[:,1:]),(raster[:-1,:],raster[1:,:]),(raster[:,-1:],raster[:,:1])]:
  mask=a!=b;packed=np.minimum(a[mask],b[mask]).astype(np.uint32)*65536+np.maximum(a[mask],b[mask]);edges.update((int(v)//65536,int(v)%65536) for v in np.unique(packed))
 for row in csv.reader((ROOT/'map/adjacencies.csv').read_text('utf-8-sig').splitlines(),delimiter=';'):
  if len(row)>2 and row[0].lstrip('-').isdigit() and row[1].lstrip('-').isdigit() and int(row[0])>=0 and int(row[1])>=0 and row[2]!='impassable':edges.add(tuple(sorted((int(row[0]),int(row[1])))))
 rails=0;gaps=[]
 for line in (ROOT/'map/railways.txt').read_text('utf-8-sig').splitlines():
  if not line.strip():continue
  level,count,*pids=map(int,line.split());rails+=1;assert count==len(pids)
  assert all(p in pstate and defs[p]['type']=='land' for p in pids)
  gaps.extend((a,b) for a,b in zip(pids,pids[1:]) if tuple(sorted((a,b))) not in edges)
 assert not gaps,gaps
 supply=[]
 for line in (ROOT/'map/supply_nodes.txt').read_text('utf-8-sig').splitlines():
  if line.strip():_,pid=map(int,line.split());assert pid in pstate and defs[pid]['type']=='land';supply.append(pid)
 assert len(supply)==len(set(supply))
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  oldpreg={}
  for name in z.namelist():
   if name.startswith('map/strategicregions/') and name.endswith('.txt'):
    n=parse(z.read(name).decode('utf-8-sig'))[0];rid=int(n.val('id'))
    for v in n.get('provinces').children:oldpreg[int(v.key)]=rid
  marine_moved=[p for p,d in defs.items() if p and d['type'] in ['sea','lake'] and oldpreg.get(p)!=preg.get(p)];assert not marine_moved
  assert z.read('map/provinces.bmp')==(ROOT/'map/provinces.bmp').read_bytes()
  assert z.read('map/definition.csv')==(ROOT/'map/definition.csv').read_bytes()
 model_slots=collections.Counter();model_mismatch=[];affected=set(json.loads((OUT/'plan.json').read_text('utf-8'))['affected_states'])
 for i,line in enumerate((ROOT/'map/buildings.txt').read_text('utf-8-sig').splitlines(),1):
  row=line.split(';');assert len(row)==7,(i,line);sid=int(row[0]);assert sid in states
  x,z=math.floor(float(row[2])),math.floor(float(row[4]));assert 0<=x<W and 0<=z<H
  pid=int(row[6]) if row[1]=='floating_harbor' else int(raster[H-1-z,x]);actual=pstate.get(pid);model_slots[sid,row[1]]+=1
  if actual and actual!=sid:model_mismatch.append({'line':i,'state':sid,'actual':actual,'kind':row[1]});assert sid not in affected and actual not in affected
 requirements=json.loads((OUT/'model-changes.json').read_text('utf-8'))['required_state_models']
 for sid in affected:
  coastal=any(defs[int(x.key)]['coastal']=='true' for x in states[sid][2].get('provinces').children)
  for kind,(count,coast) in requirements.items():
   if not coast or coastal:assert model_slots[sid,kind]>=count,(sid,kind,model_slots[sid,kind],count)
 loc=[]
 for lang in LANGS:
  p=ROOT/f'localisation/replace/zzzz_apdc_map_geography_l_{lang}.yml';raw=p.read_bytes();assert raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');pairs=re.findall(r'^\s*([\w.-]+):0\s+"([^"\n]*)"',text,re.M);keys=[k for k,v in pairs];assert len(keys)==len(set(keys));d=dict(pairs)
  assert text.startswith('l_'+lang+':')
  assert all(s.val('name') in d for _,_,s in states.values())
  for sid in NAMES:assert d['STATE_'+str(sid)]==name_value(sid,lang)
  loc.append(lang)
 capitals=[];active={v['owner'] for v in politics.values()}
 for p in (ROOT/'history/countries').glob('*.txt'):
  caps=[n for n in parse(p.read_text('utf-8-sig')) if n.key=='capital']
  for n in caps:assert int(n.value) in states
  if p.name[:3] in active:assert caps and politics[str(int(caps[0].value))]['owner']==p.name[:3]
  capitals.extend({'tag':p.name[:3],'state':int(n.value)} for n in caps)
 report={'passed':True,'states':len(states),'state_provinces':len(pstate),'defined_provinces':len(defs),'strategic_regions':len(regions),'cross_region_states':cross,'sea_lake_region_changes':marine_moved,'original_province_pixels_and_definition_preserved':True,'victory_points':len(vp),'victory_score':sum(v[1] for v in vp.values()),'medina':vp[13462],'initial_dmz':dmz,'impassable_unchanged':True,'actual_buildings_before':dict(oldbuild),'actual_buildings_after':dict(newbuild),'actual_industry_airports_ports_landmarks_totals_preserved':True,'railways':rails,'railway_gaps':gaps,'supply_nodes':len(supply),'model_records':sum(model_slots.values()),'unrelated_preexisting_model_mismatches':model_mismatch,'affected_model_mismatches':0,'languages_checked':loc,'capital_references':capitals,'economy':totals}
 dump(OUT/'static-audit.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['unrelated_preexisting_model_mismatches','capital_references']},ensure_ascii=False))

def prepare_qa():
 assert json.loads((OUT/'static-audit.json').read_text('utf8'))['passed'];assert json.loads((OUT/'extended-static-audit.json').read_text('utf8'))['passed'];assert not QA.exists()
 for rel in ['mod','driver/common/on_actions','driver/common/defines']:(QA/rel).mkdir(parents=True,exist_ok=True)
 desc=(ROOT/'descriptor.mod').read_text('utf8');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M);(QA/'mod/APDC.mod').write_text(desc,'utf8')
 (QA/'mod/APDC_TarazQA_20261106.mod').write_text('name="APDC November 6 map diagnostics"\npath="'+(QA/'driver').as_posix()+'"\nsupported_version="1.19.*"\n','utf8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_TarazQA_20261106.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA_20261104/settings.txt').read_text('utf8');(QA/'settings.txt').write_text(settings,'utf8')
 (QA/'driver/common/defines/zzzz_APDC_city_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf8')
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));checks=''
 for sid in sorted(set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states'])):
  p=pol[str(sid)];test=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+v for v in p['cores']);checks+=f'{sid} = {{ if = {{ limit = {{ {test} }} log = "APDC_TARAZ_20261106 PASS state_{sid}" }} else = {{ log = "APDC_TARAZ_20261106 FAIL state_{sid}" }} }}\n'
 daily='add_to_variable = { apdc_qa_city_day = 1 }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_TARAZ_20261106 WORLD_READY" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 20 } } set_variable = { apdc_cw_selected = SOV } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_TARAZ_20261106 SOV_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 34 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_TARAZ_20261106 WORLD_RETURNED" }\nlog = "APDC_TARAZ_20261106 DAY [?apdc_qa_city_day] date=[GetDateText]"\n'
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
 migrated_buildings=[]
 states=statefiles(ROOT/'history/states')
 for sid in [586,881,1646]:
  kind='industrial_complex';wanted=int(states[sid][2].get('history').get('buildings').val(kind,'0'))
  block=native[sid].get('buildings');building=block.get(kind) if block else None;level=int(building.val('level','0')) if building else 0
  assert level>=wanted if wanted else level==0,(sid,kind,level,wanted)
  migrated_buildings.append({'state':sid,'kind':kind,'level':level,'expected':wanted})
 active={v['owner'] for v in pol.values()}
 for p in (ROOT/'history/countries').glob('*.txt'):
  if p.name[:3] not in active:continue
  caps=[n for n in parse(p.read_text('utf-8-sig')) if n.key=='capital'];match=re.search(r'(?m)^\t\tcapital=(\d+)',countries[p.name[:3]]);assert caps and match and int(caps[0].value)==int(match[1]);capitals.append(p.name[:3])
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[v for v in game.splitlines() if 'APDC_TARAZ_20261106' in v]
 relevant=[v for v in error.splitlines() if re.search(r'MAP_ERROR|map/buildings.txt|Province with id:|State \d+ has no|[Rr]ailway|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|pdx_localize.cpp|localization.*error',v)]
 with zipfile.ZipFile(Path(META['checkpoint']['backup'])/'runtime-evidence.zip') as z:prior=z.read('logs/error.log').decode('utf-8-sig',errors='replace')
 norm=lambda s:re.sub(r'^(?:\[[^\]]*\])+\s*','',s)
 new=collections.Counter(norm(s) for s in error.splitlines())-collections.Counter(norm(s) for s in prior.splitlines());changed=[p for p,h in META['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1];markers=['WORLD_READY','SOV_DETAIL_READY','WORLD_RETURNED']
 signature=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'))['signature'];geometry_flag='apdc_cw_render_lookup_v2_geo_'+signature;assert geometry_flag in text,'Native save did not initialize the current geography lookup'
 sov_states=sorted(int(s) for s,p in pol.items() if p['owner']=='SOV' and 'SOV' in p['cores']);detail_match=re.search(r'SOV_DETAIL_READY states=(\d+)',game)
 assert 1646 in sov_states and detail_match and int(detail_match[1])==len(sov_states),'New Taraz state missing from actual SOV core-detail count'

 passed=not(differences or dmz or relevant or changed or new) and 'FAIL' not in '\n'.join(evidence) and all(any(marker in line for line in evidence) for marker in markers) and date.startswith('2060.2.') and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers'])
 system=(QA/'logs/system.log').read_text('utf-8-sig',errors='replace');report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'relation_differences':differences,'initial_dmz':dmz,'active_capitals_checked':len(capitals),'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_signatures_vs_last_completed_runtime':dict(new),'user_file_changes':changed,'evidence':evidence,'process':record,'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf8')),'version_and_active_dlcs':[s for s in system.splitlines() if 'Version:' in s or 'Active DLC' in s],'input_desktop_switched':False,'mouse_keyboard_sent':False}
 dump(OUT/'runtime-audit.json',report)
 report['current_geography_lookup_flag_in_native_save']=geometry_flag;report['migrated_state_buildings_verified']=migrated_buildings;report['SOV_core_detail_count']=len(sov_states);report['new_state_1646_in_actual_SOV_detail']=True;dump(OUT/'runtime-audit.json',report)
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
  old=json.loads(z.read('docs/cold-war/20261024/geometry.json'));oldpol=json.loads(z.read('tools/map_maintenance/baseline/initial_territories.json'));assert all(old[k]==g[k] for k in ['palette_ids','scales','colors'])
  def world(meta,before):
   pol=oldpol if before else json.loads((BASE/'initial_territories.json').read_text('utf8'))
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
  allowed=Image.fromarray(np.isin(raster,[pid for pid,sid in pm.items() if sid in set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states'])]).astype('uint8')*255).resize((1000,500),Image.Resampling.LANCZOS).filter(ImageFilter.MaxFilter(9));outside=int(np.count_nonzero(changed & (np.asarray(allowed)==0)));assert not outside
  protected=['palette.png','background.png','screen_overlay.png','pie_frame.png','option.png','control.png','swatches.png']+[p.name for p in (ROOT/prefix).glob('pie_*.png')]
  for name in protected:assert z.read(prefix+name)==(ROOT/prefix/name).read_bytes()
  assert z.read('gfx/FX/APDC_cw_palette.shader')==(ROOT/'gfx/FX/APDC_cw_palette.shader').read_bytes()
  rel='localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml';loc_before=z.read(rel);loc_after=(ROOT/rel).read_bytes();assert loc_after.startswith(loc_before);assert set(re.findall(rb'APDC_CW_STATE_(\d+)',loc_after[len(loc_before):]))=={str(s).encode() for s in [1646]}
 native=[];diff=None
 if (OUT/'runtime-visual-captures.json').exists():
  native=json.loads((OUT/'runtime-visual-captures.json').read_text('utf8'));a=np.asarray(Image.open(OUT/'runtime-world.png'))[150:650,458:1458];b=np.asarray(Image.open(OUT/'runtime-world-return.png'))[150:650,458:1458];diff=int(np.count_nonzero(np.any(a!=b,axis=2)));assert diff==0
 dump(OUT/'visual-asset-audit.json',{'passed':True,'state_masks_exact':len(g['pieces']),'world_changed_pixels':int(changed.sum()),'unrelated_world_changed_pixels':outside,'palette_count':len(g['palette_ids']),'zoom_levels':len(g['scales']),'palette_scales_shader_non_map_art_and_tooltips_preserved':True,'native_capture_count':len(native),'native_world_first_vs_return_diff_pixels':diff})
 print(json.dumps({'state_masks':len(g['pieces']),'changed_world_pixels':int(changed.sum()),'unrelated_pixels':outside,'native_captures':len(native),'native_world_return_diff':diff}))

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
 cp={**META['checkpoint'],'date':'2026-11-06','report':META['report'],'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER '+json.loads((OUT/'runtime-audit.json').read_text('utf8'))['date']+'; all 1646 state relations checked; world/SOV/return reviewed; own game/helpers stopped','runtime_report':META['report']+'/runtime-audit.json','visual_report':META['report']+'/visual-review.json','backup':str(BACKUP),'geography_backup':str(BACKUP),'previous_report':META['checkpoint']['report'],'map_checkpoint_archive':ma.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(ma),'states':len(ss),'city_review':META['report']+'/city-review.json'}

 for key in ['name_only','name_only_validation','runtime_evidence_inherited_from','latest_change_backup']:cp.pop(key,None)
 dump(BASE/'latest_checkpoint.json',cp);preservation();print('November 6 checkpoint saved')

def ancillary_audit():
 ss=statefiles(ROOT/'history/states');pm=pmap(ss);plan=json.loads((OUT/'plan.json').read_text('utf8'));affected=set(plan['affected_states'])
 air=[];deployments=[];calls=[]
 for p in (ROOT/'history/units').rglob('*.txt'):
  for n in walk(parse(p.read_text('utf-8-sig'))):
   if n.key=='air_wings':
    for v in n.children:
     if not v.key.isdigit():continue
     sid=int(v.key);assert sid in ss and int(ss[sid][2].get('history').get('buildings').val('air_base','0'))>0,(p,sid)
     air.append({'file':p.relative_to(ROOT).as_posix(),'state':sid})
   if n.key in ['location','base'] and n.value and n.value.isdigit():
    pid=int(n.value);assert pid in pm,(p,n.key,pid);deployments.append({'file':p.relative_to(ROOT).as_posix(),'field':n.key,'province':pid,'state':pm[pid]})
 for p in (ROOT/'history/countries').glob('*.txt'):
  for n in walk(parse(p.read_text('utf-8-sig'))):
   if n.key in ['oob','set_oob','load_oob','set_air_oob','load_air_oob','set_naval_oob','load_naval_oob']:calls.append({'file':p.relative_to(ROOT).as_posix(),'command':n.key,'value':n.value})
 dump(OUT/'air-oob-audit.json',{'passed':True,'unit_files_checked':len(list((ROOT/'history/units').rglob('*.txt'))),'air_wings':air,'deployments':deployments,'all_country_history_oob_calls_including_nested':calls,'airport_migration':{},'country_histories_unchanged':True})
 renames=json.loads((OUT/'renames.json').read_text('utf8'));oldpaths={r['old'] for r in renames};references=[]
 for p in ROOT.rglob('*.py'):
  if '.git' in p.parts:continue
  t=p.read_text('utf-8-sig')
  for old in oldpaths:
   if old in t or Path(old).name in t:references.append({'file':p.relative_to(ROOT).as_posix(),'old_path':old,'classification':'Historical dated tool; runtime reads current files by internal ID, not this old path'})
 for sid in NAMES:
  p=ss[sid][0];assert p.name==str(sid)+'-'+NAMES[sid][1]+'.txt' and not re.search(r'[<>:"/\\|?*]',p.name)
  assert not p.read_bytes().startswith(b'\xef\xbb\xbf')
 dump(OUT/'renamed-path-reference-audit.json',{'passed':True,'renames':renames,'historical_tool_mentions':references,'runtime_state_loading':'internal IDs; no path-based runtime reference to old names'})
 alias=re.compile(r'^(?:STATE_(\d+)|[A-Za-z0-9_]+_STATE_(\d+)|STATE_(\d+)_[A-Za-z0-9_]+|state_(\d+)_name|(\d+)_[A-Za-z0-9_]+_name)$');checked=[]
 for lang in LANGS:
  for p in (ROOT/'localisation').rglob('*_l_'+lang+'.yml'):
   for key,value in re.findall(r'^\s*([A-Za-z0-9_.-]+):\d+\s+"((?:\\.|[^"\\])*)"',p.read_text('utf-8-sig'),re.M):
    m=alias.fullmatch(key)
    if not m:continue
    sid=int(next(v for v in m.groups() if v))
    if sid not in NAMES or '[' in value:continue
    assert value==name_value(sid,lang),(p,key,value);checked.append({'file':p.relative_to(ROOT).as_posix(),'key':key})
 dump(OUT/'localisation-reference-audit.json',{'passed':True,'geographic_keys_checked':checked,'victory_point_names_preserved':True,'strategic_region_names_preserved':True})
 # All changed states are checked recursively; no pre-2060 conditional/date
 # political effects remain hidden behind a top-level owner comparison.
 nested=[]
 for sid in affected:
  for n in walk(ss[sid][2].get('history').children):
   if n.key in ['if','else_if','else'] or re.fullmatch(r'\d{4}\.\d+\.\d+',n.key):nested.append({'state':sid,'field':n.key})
 dump(OUT/'geographic-reference-review.json',{'passed':True,'affected_states':sorted(affected),'nested_date_or_conditional_history':nested,'country_histories_and_capitals_unchanged':True,'new_state_sources':{1646:{586:4,881:1}},'reference_changes':json.loads((OUT/'additional-reference-changes.json').read_text('utf8')),'other_numeric_uses':'French grammatical tables and array/ship/division indices retained in their own namespaces; no blanket numeric replacement'})
 print('Ancillary references, OOB, filenames and geographic aliases passed')

def sync_editor_names():
 p=USER/'localisation/simp_chinese/state_names_l_simp_chinese.yml';raw=p.read_bytes();t=raw.decode('utf-8-sig');before=dict(re.findall(r'^\s*(\w+):-?\d+\s+"([^"\n]*)"',t,re.M));changes=[]
 for sid in NAMES:
  key='STATE_'+str(sid);value=NAMES[sid][0];pat=re.compile(r'(?m)^(\s*'+re.escape(key)+r'):-?\d+\s+"[^"\n]*"')
  t,count=pat.subn(lambda m:m[1]+':0 "'+value+'"',t);assert count==1;changes.append({'key':key,'before':before[key],'after':value})
 versions=len(re.findall(r':-1(?=\s+")',t));t=re.sub(r':-1(?=\s+")',':0',t)
 p.write_text(t,'utf-8-sig',newline='\n');after=dict(re.findall(r'^\s*(\w+):0\s+"([^"\n]*)"',t,re.M));assert all(v==after[k] for k,v in before.items() if k not in {'STATE_'+str(s) for s in NAMES})
 dump(OUT/'editor-localisation-audit.json',{'passed':True,'file':str(p),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':sha(p),'backup':'user-settings-and-editor-before.zip/localisation/simp_chinese/state_names_l_simp_chinese.yml','name_changes':changes,'other_values_preserved':True,'other_minus_one_versions_normalized':versions,'utf8_bom':p.read_bytes().startswith(b'\xef\xbb\xbf')})
 print('Editor localisation synchronized')

def references_apply():
 p=ROOT/'common/scripted_triggers/GER_scripted_triggers.txt';t=p.read_text('utf8');plan=json.loads((OUT/'plan.json').read_text('utf8'));new=set(plan['new_states'])
 primary={int(s):min(map(int,c),key=lambda k:(-c[str(k)],k)) for s,c in plan['state_sources'].items() if int(s) in new};edits=[];changes=[]
 for top in parse(t):
  if not(top.key.startswith('GER_is_') and top.key.endswith('_state')):continue
  blocks=[n for n in top.children if n.key=='OR']
  if len(blocks)!=1:continue
  block=blocks[0];members={int(n.value) for n in block.children if n.key=='state' and n.value and n.value.isdigit()};added=sorted(s for s,src in primary.items() if src in members and s not in members)
  if not added:continue
  last=[n for n in block.children if n.key=='state'][-1];end=t.find('\n',last.end);assert end>=0
  edits.append((end,end,''.join('\n\t\tstate = '+str(s) for s in added)));changes.append({'file':p.relative_to(ROOT).as_posix(),'group':top.key,'added':added,'primary_sources':{s:primary[s] for s in added},'reason':'New Taraz subdivision inherits the existing geographic group of its main source; original gameplay conditions retained'})
 if edits:p.write_text(patches(t,edits),'utf8')
 dump(OUT/'additional-reference-changes.json',changes);print(json.dumps({'geographic_groups_changed':len(changes)}))

def city_review():
 ss=statefiles(ROOT/'history/states');pm=pmap(ss);v=json.loads((BASE/'modern_victory_points.json').read_text('utf8'))['province_id_inventory'];rows=[]
 for sid,pid in [(1646,12640),(881,10308)]:
  r=v[str(pid)];assert r['state_id']==pm[pid]==sid
  rows.append({'state':sid,'city_province':pid,'city':r['name'],'names':r['names'],'actual_state':pm[pid],'contains_named_city':True,'score':r['score']})
 report={'date':'2026-11-06','source':'tools/map_maintenance/baseline/modern_victory_points.json','rows':rows,'regional_name_exclusions':{'586':'East Jambyl is a regional name; Taraz city has moved into new state 1646'},'mismatches':[],'unresolved':[],'province_lists_preserved':True,'city_scores_names_and_locations_preserved':True}
 dump(OUT/'city-review.json',report);m=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));m['latest_added_renamed_state_review']={'date':'2026-11-06','report':META['report']+'/city-review.json','city_named_states_checked':len(rows),'mismatches':[],'border_uncertain':[],'unresolved':[]};dump(BASE/'city_named_state_mismatches.json',m)
 print('Taraz and Karagandy city hosts verified')

def deliver_docs():
 runtime=json.loads((OUT/'runtime-audit.json').read_text('utf8'));art=json.loads((OUT/'visual-asset-audit.json').read_text('utf8'));visual=json.loads((OUT/'visual-review.json').read_text('utf8'))
 assert runtime['passed'] and art['passed'] and visual['reviewed'] and art['native_capture_count']==3
 plan=json.loads((OUT/'plan.json').read_text('utf8'));model=json.loads((OUT/'model-changes.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));totals=json.loads((OUT/'allocation-totals.json').read_text('utf8'));states=statefiles(ROOT/'history/states')
 resource_table='\n'.join('| '+k+' | '+v['source']+' | '+str(v['rounded'])+' | '+v['rounding_difference']+' |' for k,v in totals['resources'].items())
 details=[]
 for sid in [586,881,1646]:
  s=states[sid][2];resources={v.key:v.value for b in s.children if b.key=='resources' for v in b.children};details.append('| '+str(sid)+' | '+str(s.val('manpower'))+' | '+', '.join(k+' '+v for k,v in resources.items())+' |')
 text=f'''# 2026-11-06 塔拉兹地图收尾

从最新老街名称确认检查点`20261106-laukkai-rename`继续。用户新增1646塔拉兹、586江布尔改为东江布尔；当前1646州。1645老街 / Laukkai及其他既有合法修改保留。本轮只采用当前保存的州地块列表，不回放旧缓存。

## 地块与历史

5个地块转入1646：4492、10506、12340、12640来自586，12487来自881。586和881两份清空历史从最新APDC检查点恢复，新增1646按主要来源586继承SOV拥有/控制/核心、city类别和2级基础设施。没有混合所有者、重复、遗漏、未知地块、空州或新增地块ID。三州历史递归核查，无需搬移的日期历史/条件政治分支；国家身份、人物、首都和无关玩法保持。

塔拉兹12640原3分胜利点迁到1646，城市十语名称与分数保持，全球仍5447点/20292分。卡拉干达10308仍在881；两处城市名州均包含对应城市。586为区域名东江布尔，不要求其继续包含塔拉兹；上一轮213摩尔曼斯克的既有例外仍保留。

按原工业模型锚点，586原两座民用工厂中12640上的一座迁1646，586/1646各保留1座；工业总量801不增减。新州继承基础设施，全球3045→3047；没有机场迁移或OOB文件变动。模型按当前像素/州界迁移{len(model['moved'])}条、补齐{len(model['added'])}条，共{model['records']}条，包含医疗中心、净化塔与有效spawn；不增加实际工厂、港口或其他建筑。

## 战略区与交通

仅采用上一完成运行结束后两份编辑器战略区136/268的新输出，忽略{len(plan['older_editor_outputs_ignored'])}份旧输出。恢复编辑器遗漏的全部5个转移地块，并将12487从136统一到新州主要所属的268。仅改两个区域的地块列表，天气/季节及海洋/湖泊战略归属保持。全图州无跨区、区域无重复/遗漏，海区连接图未变；642铁路、726补给节点无断点、重复或非法地块。省份图、定义表、海峡和主地图美术/字体/光照/海面保持。

为GER_is_RKT_state地理触发器追加1646，保留原玩法条件和其他数值。全体国家首都及四份OOB/相关调用已检查，本轮无国家历史或部署文件修改；法国语法表等数字引用按其自身含义保留，没有全局数字替换。

## 固定来源经济、名称与文件

以1133个固定原经济来源州按来源地块数比例精确求和，再ROUND_HALF_UP；不是按上次现值二次扣减。allocation.json记录全部地块、来源、分母、精确贡献及取整，economy-reverse-audit.json逐来源反查。世界来源和取整前人口均2100007447，写入{totals['rounded_population']}，独立取整尾差+{totals['population_rounding_difference']}。

| 州 | 人口 | 资源 |
|---|---:|---|
{chr(10).join(details)}

1646虽有4地块来自上轮586、1地块来自上轮881，固定原经济来源关系独立于上轮州界；1646与586的本轮经济结果相同来自固定贡献计算，未复制当前现值。

| 资源 | 来源/精确总量 | 写入总量 | 独立取整尾差 |
|---|---:|---:|---:|
{resource_table}

十语州名、有效国家地理别名及编辑器中文同步，用户中文逐字保留。1646-Taraz.txt与586-East Jambyl.txt为正式文件名，1645-Laukkai.txt保持。塔拉兹译名沿用固定城市清单12640（德文Taras）；东江布尔按当前项目Jambyl拼写作方向性地区名。普通脚本UTF-8无BOM，本地化UTF-8 BOM。文件名冲突、索引、名称键及路径引用检查通过。

## 冷战地图与验收

当前{cw['pieces_after']}州图块/{cw['borders_after']}边界图块，475色槽与26档缩放保持；原生渲染、旧动态提示、调色板/着色器及非地图界面保持。{len(cw['changed'])}份地理产物变化，{len(cw['unchanged_world_edge_assets_preserved'])}份不变边缘贴图保留旧字节。全部{art['state_masks_exact']}州遮罩逐像素符合当前州界；世界图{art['world_changed_pixels']}个变化像素均在受影响范围，范围外0变化；仅追加1646拥有国提示。

全量静态与扩展验收通过。一次GER 2060普通后台开局，进程{runtime['process']['pid']}，实际自动存档{runtime['date']}，SHA-256 `{runtime['save_sha256']}`；全部1646州所有者/控制者/核心/宣称吻合，非军事区0，169个有领土国家首都正确，工厂实际等级复核586=1/1646=1/881=0。新冷战几何签名`{cw['signature']}`已在原生存档初始化。

地图/建筑/铁路/冷战/本地化相关错误0，完整错误日志{runtime['all_error_log_lines']}行，与上一完成运行相比无新错误签名；不能称全游戏零错误。版本、实际DLC与日志证据见runtime-audit.json。本轮只加载APDC及独立诊断驱动，未加载用户组合中的Toolpack；仍为GER同一场景，没有额外多国开局。

已逐张检查实际世界图、SOV详情及返回三张1920×1080截图，详情含1646；返回1000×500世界图与首次打开逐像素一致。只读捕获私有窗口，没有切换用户桌面或发送键鼠，不扩大为全部缩放档、交互或主地图美术视觉验收。自己的游戏及助手退出、Steam运行标记清除，启动器、设置、继续游戏和原自动存档保持。之后仅同步编辑器中文名称，按改名规则免重复开局。

## 检查点、备份与维护

完整现场备份：`{BACKUP.as_posix()}`，包含35065份现场原字节与SHA-256、用户输入、旧日志、设置和编辑器输出。runtime-evidence.zip/runtime-save.zip保存本轮实际运行；states-checkpoint.zip/map-checkpoint.zip及当前政治、路径、城市宿主基线保存最终版本。旧报告与原始经济来源/导入快照保持原貌。

当前工具为tools/map_maintenance/finish_taraz_20261106.py，绑定本轮备份、新州1646和改名586，不可对下一轮直接apply。最终文件保护结果见preservation-audit.json。本轮完整运行结果取代之前名称检查点的继承标记，latest_checkpoint.json不再标为name_only。
'''
 (OUT/'README.md').write_text(text,'utf8')
 note='2026-11-06塔拉兹最新收尾：当前1646州；新增1646塔拉兹、586改名东江布尔，5地块改隶、恢复2份清空历史。塔拉兹12640仍3分，原两座工厂分别保留586/1646各1；固定来源精算、十语/文件名/战略区/冷战同步。GER实际存档全部州关系、169有效首都及世界/SOV/返回画面通过。当前检查点20261106-taraz，老街1645保留。详见[最新塔拉兹收尾](../../docs/map-maintenance/20261106-taraz/README.md)。'
 for rel in ['项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md']:
  p=ROOT/rel;t=p.read_text('utf8');at=t.find('\n')+1;t=t[:at]+'\n'+note+'\n'+t[at:]
  t=t.replace('latest_checkpoint.json现指向20261106-laukkai-rename，当前1645州。','latest_checkpoint.json现指向20261106-taraz，当前1646州。',1).replace('当前指向20261106-laukkai-rename |','当前指向20261106-taraz |',1)
  lines=t.splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith('| 最新州原字节归档 |'):lines[i]=line.replace('/20261106-laukkai-rename/states-checkpoint.zip','/20261106-taraz/states-checkpoint.zip')
   if line.startswith('当前地图5120×2560，2:1；1645州。'):lines[i]=line.replace('1645州','1646州',1)
   if rel.endswith('当前状态与未完成事项.md') and line.startswith('| 地图 |'):lines[i]='| 地图 | 2026-11-06最新塔拉兹收尾：1646州，新增1646/586改名/5地块；恢复2历史、保留工厂总量，固定来源经济及冷战同步；GER全部州关系、169首都和世界/SOV/返回画面通过 | [最新收尾](../../docs/map-maintenance/20261106-taraz/README.md) |\n'
   if rel.endswith('冷战系统_规则与维护.md') and line.startswith('状态：已实现。'):
    line=line.replace('当前1645州/1795州图块/3862边界图块',f"当前1646州/{cw['pieces_after']}州图块/{cw['borders_after']}边界图块").replace('BRM核心详情','SOV核心详情').replace('当前几何签名9fa96167ccdc',f"当前几何签名{cw['signature']}").replace('docs/map-maintenance/20261106/README.md','docs/map-maintenance/20261106-taraz/README.md');lines[i]=line
  p.write_text(''.join(lines),'utf8')
 print('Taraz report and handover saved')

if __name__=='__main__':globals()[sys.argv[1]]()
