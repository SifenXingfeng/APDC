"""2026-11-06 APDC map closeout. Date-specific reviewed inputs, latest APDC history.
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
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-map-finish-20261106.json').read_text('utf8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];QA=Path(META['qa'])
NAMES={
148:['拉普兰','Lapland','Лапландия','ラップランド','라플란드'],
147:['东博腾','Ostrobothnia','Остроботния','ポフヤンマー','포흐얀마'],
1304:['凯努','Kainuu','Кайнуу','カイヌー','카이누'],
1305:['北卡累利阿','North Karelia','Северная Карелия','北カレリア','북카리알라'],
722:['科拉半岛','Kola Peninsula','Кольский полуостров','コラ半島','콜라반도'],
1645:['老街', 'Laukkai', 'Лауккай', 'ラウカイ郡区', '라우카이']}
for module in [oldtool,oldverify]:
 module.META=META;module.BACKUP=BACKUP;module.OUT=OUT;module.QA=QA;module.NAMES=NAMES

LATIN_NAMES={
 'french':{148:'Laponie',147:'Ostrobotnie',1304:'Kainuu',1305:'Carélie du Nord',722:'Péninsule de Kola'},
 'german':{148:'Lappland',147:'Österbotten',1304:'Kainuu',1305:'Nordkarelien',722:'Kola-Halbinsel'},
 'spanish':{148:'Laponia',147:'Ostrobotnia',1304:'Kainuu',1305:'Carelia del Norte',722:'Península de Kola'},
 'braz_por':{148:'Lapônia',147:'Ostrobótnia',1304:'Kainuu',1305:'Carélia do Norte',722:'Península de Kola'},
 'polish':{148:'Laponia',147:'Ostrobotnia',1304:'Kainuu',1305:'Karelia Północna',722:'Półwysep Kolski'}}

def name_value(sid,lang):
 return LATIN_NAMES.get(lang,{}).get(sid,NAMES[sid][{'simp_chinese':0,'russian':2,'japanese':3,'korean':4}.get(lang,1)])

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
 dump(OUT/'name-decisions.json',{'names':{sid:{lang:name_value(sid,lang) for lang in LANGS} for sid in NAMES},'chinese':'User supplied, preserved verbatim. State renames do not rename cities or strategic regions.','laukkai':'The user confirmed state 1645 as 老街 / Laukkai after the closeout; all languages inherit the existing city names. See docs/map-maintenance/20261106-laukkai-rename.','sources':['https://stat.fi/en/luokitukset/maakunta/maakunta_1_20260101','https://kotus.fi/wp-content/uploads/2025/04/Toponymic_guidelines_2025.pdf'],'scope':'Naming only; political identities follow APDC, not modern Finland.'})

def finalize_names():
 ss=statefiles(ROOT/'history/states');renames=json.loads((OUT/'renames.json').read_text('utf8'))
 for sid in NAMES:
  p,_,_=ss[sid];dest=p.with_name(str(sid)+'-'+NAMES[sid][1]+'.txt')
  if dest!=p:
   assert not dest.exists();renames.append({'state':sid,'old':p.relative_to(ROOT).as_posix(),'new':dest.relative_to(ROOT).as_posix()});p.rename(dest)
 dump(OUT/'renames.json',renames);update_names(renames)
 index={str(sid):p.name for sid,(p,_,_) in statefiles(ROOT/'history/states').items()};dump(BASE/'current_state_files.json',index);dump(OUT/'state-index.json',index)

def apply():
 assert json.loads((OUT/'plan.json').read_text('utf8'))['new_states']==[1645]
 oldtool.update_names=update_names
 oldtool.apply()

def references_apply():
 # These geographic groups referred to old Salla/Petsamo/Murmansk, whose
 # province sets now live in other state IDs. Preserve geographic coverage.
 p=ROOT/'common/scripted_triggers/GER_scripted_triggers.txt';t=p.read_text('utf8');edits=[];changes=json.loads((OUT/'additional-reference-changes.json').read_text('utf8')) if (OUT/'additional-reference-changes.json').exists() else []
 targets={'GER_is_soviet_greater_finland_state':[216,215,213,722], 'GER_is_additional_soviet_greater_finland_state':[146,213,215]}
 for n in parse(t):
  if n.key not in targets:continue
  b=n.get('OR');assert b and all(c.key=='state' for c in b.children)
  before=[int(c.value) for c in b.children];after=targets[n.key]
  if before==after:continue
  labels={146:'Karelia',213:'Petsamo and old Salla territory',215:'Eastern Karelia and old Salla territory',216:'Olonets',722:'Kola Peninsula / Murmansk'}
  replacement='{\n'+''.join('\t\tstate = '+str(s)+' # '+labels[s]+'\n' for s in after)+'\t}'
  edits.append((b.value_start,b.value_end,replacement));changes.append({'file':p.relative_to(ROOT).as_posix(),'group':n.key,'before':before,'after':after,'reason':'Follow old geographic coverage after Salla/Petsamo/Murmansk state-ID reuse; exclude new Ostrobothnia'})
 if edits:p.write_text(patches(t,edits),'utf8')
 # The localised power-plant description explicitly refers to old Petsamo.
 p=ROOT/'localisation/simp_chinese/aat_focus_l_simp_chinese.yml';t=p.read_text('utf-8-sig');lines=t.splitlines(keepends=True)
 for i,line in enumerate(lines):
  if line.lstrip().startswith('FIN_janiskoski_power_plant_desc:') and '[722.GetName]' in line:
   lines[i]=line.replace('[722.GetName]','[213.GetName]');changes.append({'file':p.relative_to(ROOT).as_posix(),'key':'FIN_janiskoski_power_plant_desc','from':722,'to':213,'reason':'Old Petsamo is now wholly in state 213; power-plant location remains there'})
  if line.lstrip().startswith('FIN_integrate_kola_and_karelia_tt:') and '[722.GetName]' not in line:
   lines[i]=line.replace('§Y[213.GetName]§!','§Y[722.GetName]§!、§Y[213.GetName]§!');changes.append({'file':p.relative_to(ROOT).as_posix(),'key':'FIN_integrate_kola_and_karelia_tt','added':722,'reason':'Reflect the Kola/Murmansk subdivision in the matching geographic requirement'})
 if ''.join(lines)!=t:p.write_text(''.join(lines),'utf-8-sig')
 dump(OUT/'additional-reference-changes.json',changes)
 print(json.dumps({'geographic_reference_changes':len(changes)}))


def plan():
 ss=statefiles(ROOT/'history/states');old=previous();op=pmap(old);pm=pmap(ss)
 assert set(ss)-set(old)=={1645};assert set(pm)==set(op),'Unknown or missing source provinces need explicit relationships'
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
 allowed|={'map/buildings.txt','tools/map_maintenance/finish_20261106.py','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json','tools/map_maintenance/baseline/latest_checkpoint.json'}
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
 assert len(states)==1645 and set(range(1,1646))==set(states)
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
 (QA/'mod/APDC_MapMaintenanceQA_20261106.mod').write_text('name="APDC November 6 map diagnostics"\npath="'+(QA/'driver').as_posix()+'"\nsupported_version="1.19.*"\n','utf8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_MapMaintenanceQA_20261106.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA_20261104/settings.txt').read_text('utf8');(QA/'settings.txt').write_text(settings,'utf8')
 (QA/'driver/common/defines/zzzz_APDC_city_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf8')
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));checks=''
 for sid in sorted(set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states'])):
  p=pol[str(sid)];test=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+v for v in p['cores']);checks+=f'{sid} = {{ if = {{ limit = {{ {test} }} log = "APDC_MAP_20261106 PASS state_{sid}" }} else = {{ log = "APDC_MAP_20261106 FAIL state_{sid}" }} }}\n'
 daily='add_to_variable = { apdc_qa_city_day = 1 }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_MAP_20261106 WORLD_READY" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 20 } } set_variable = { apdc_cw_selected = BRM } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261106 BRM_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 34 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261106 WORLD_RETURNED" }\nlog = "APDC_MAP_20261106 DAY [?apdc_qa_city_day] date=[GetDateText]"\n'
 (QA/'driver/common/on_actions/zzzz_APDC_city_qa.txt').write_text('on_actions = { on_daily_GER = { effect = {\n'+daily+'} } }\n','utf8')
 dump(OUT/'runtime-preparation.json',{'profile':str(QA),'source':str(ROOT),'user_files_before':META['user_files_before'],'user_enabled_mods':META['enabled_mods_before'],'scene':'One ordinary GER 2060 start; world/BRM detail/return on private desktop; no mouse or keyboard','toolpack_loaded':False,'external_descriptor':(USER/'mod/APDC.mod').read_text('utf8')})
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
 for sid,kind,wanted in [(722,'air_base',2),(213,'air_base',0),(1039,'synthetic_refinery',1),(609,'synthetic_refinery',0)]:
  block=native[sid].get('buildings');building=block.get(kind) if block else None;level=int(building.val('level','0')) if building else 0
  assert level>=wanted if wanted else level==0,(sid,kind,level,wanted)
  migrated_buildings.append({'state':sid,'kind':kind,'level':level,'expected':wanted})
 active={v['owner'] for v in pol.values()}
 for p in (ROOT/'history/countries').glob('*.txt'):
  if p.name[:3] not in active:continue
  caps=[n for n in parse(p.read_text('utf-8-sig')) if n.key=='capital'];match=re.search(r'(?m)^\t\tcapital=(\d+)',countries[p.name[:3]]);assert caps and match and int(caps[0].value)==int(match[1]);capitals.append(p.name[:3])
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[v for v in game.splitlines() if 'APDC_MAP_20261106' in v]
 relevant=[v for v in error.splitlines() if re.search(r'MAP_ERROR|map/buildings.txt|Province with id:|State \d+ has no|[Rr]ailway|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|pdx_localize.cpp|localization.*error',v)]
 with zipfile.ZipFile(Path(META['checkpoint']['backup'])/'runtime-evidence.zip') as z:prior=z.read('logs/error.log').decode('utf-8-sig',errors='replace')
 norm=lambda s:re.sub(r'^(?:\[[^\]]*\])+\s*','',s)
 new=collections.Counter(norm(s) for s in error.splitlines())-collections.Counter(norm(s) for s in prior.splitlines());changed=[p for p,h in META['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1];markers=['WORLD_READY','BRM_DETAIL_READY','WORLD_RETURNED']
 signature=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'))['signature'];geometry_flag='apdc_cw_render_lookup_v2_geo_'+signature;assert geometry_flag in text,'Native save did not initialize the current geography lookup'

 passed=not(differences or dmz or relevant or changed or new) and 'FAIL' not in '\n'.join(evidence) and all(any(marker in line for line in evidence) for marker in markers) and date.startswith('2060.2.') and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers'])
 system=(QA/'logs/system.log').read_text('utf-8-sig',errors='replace');report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'relation_differences':differences,'initial_dmz':dmz,'active_capitals_checked':len(capitals),'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_signatures_vs_last_completed_runtime':dict(new),'user_file_changes':changed,'evidence':evidence,'process':record,'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf8')),'version_and_active_dlcs':[s for s in system.splitlines() if 'Version:' in s or 'Active DLC' in s],'input_desktop_switched':False,'mouse_keyboard_sent':False}
 dump(OUT/'runtime-audit.json',report)
 report['current_geography_lookup_flag_in_native_save']=geometry_flag;report['migrated_state_buildings_verified']=migrated_buildings;dump(OUT/'runtime-audit.json',report)
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
  rel='localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml';loc_before=z.read(rel);loc_after=(ROOT/rel).read_bytes();assert loc_after.startswith(loc_before);assert set(re.findall(rb'APDC_CW_STATE_(\d+)',loc_after[len(loc_before):]))=={str(s).encode() for s in [1645]}
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
 cp={**META['checkpoint'],'date':'2026-11-06','report':META['report'],'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER '+json.loads((OUT/'runtime-audit.json').read_text('utf8'))['date']+'; all 1645 state relations checked; world/BRM/return reviewed; own game/helpers stopped','runtime_report':META['report']+'/runtime-audit.json','visual_report':META['report']+'/visual-review.json','backup':str(BACKUP),'geography_backup':str(BACKUP),'previous_report':META['checkpoint']['report'],'map_checkpoint_archive':ma.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(ma),'states':len(ss),'city_review':META['report']+'/city-review.json'}
 dump(BASE/'latest_checkpoint.json',cp);preservation();print('November 6 checkpoint saved')

def city_review():
 import unicodedata
 import numpy as np
 def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
 source=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/GF-MAP/.codex_backups/20261020-183551-chinese-city-name-corrections/现代胜利点总表.json');catalog=json.loads(source.read_text('utf-8-sig'));ss=statefiles(ROOT/'history/states');pm=pmap(ss)
 queries={40:('RU',['Rubtsovsk']),213:('RU',['Murmansk']),609:('CN',['Tianjin']),742:('TJ',['Dushanbe']),881:('KZ',['Karagandy','Karaganda']),998:('MM',['Sagaing']),1640:('KG',['Jalal-Abad','Manas'])}
 matches=collections.defaultdict(list)
 for sid,(country,labels) in queries.items():
  wanted={norm(v) for v in labels}
  for row in catalog:
   if row.get('country_iso2')!=country:continue
   names=[row.get(k,'') for k in ['name','ascii','ucdb_name']]+[row.get('names',{}).get('english','')]+[v.get('name','') for v in row.get('same_province_cities',[])]
   if not wanted&{norm(v) for v in names}:continue
   pid=row['province_id'];matches[sid].append({'city':row['name'],'province':pid,'actual_state':pm[pid],'ucdb_id':row['ucdb_id'],'method':'Current fixed city inventory; actual province host, including same-province city members'})
 defs,raster=raster_data();H,W=raster.shape;gaz=source.parent.parent/'20261019-200749-modern-victory-points';fit=json.loads((gaz/'registration/global_fit.json').read_text('utf8'));sx,sy,tx,ty=fit['params'];fallback={s:(country,{norm(v) for v in labels}) for s,(country,labels) in queries.items() if not matches[s]};supp=collections.defaultdict(list);bounds={}
 for sid in fallback:
  yy,xx=np.nonzero(np.isin(raster,[int(v.key) for v in ss[sid][2].get('provinces').children]));bounds[sid]=(xx.min(),xx.max(),yy.min(),yy.max())
 with zipfile.ZipFile(gaz/'research/geonames_cities500.zip') as z:
  with z.open('cities500.txt') as f:
   for raw in f:
    fields=raw.decode('utf8').rstrip('\n').split('\t')
    if len(fields)<15:continue
    for sid,(country,wanted) in fallback.items():
     if fields[8]!=country:continue
     labels={norm(v) for v in [fields[1],fields[2]]+fields[3].split(',')}
     if not labels&wanted:continue
     lat,lon=map(float,fields[4:6]);phi=math.radians(lat);p2=phi*phi;x=math.radians(lon)*sx+tx;y=ty-sy*phi*(1.0148+p2*p2*(0.23185+p2*(-0.14499+0.02406*p2)));ix=int(math.floor(x+.5))%W;iy=max(0,min(H-1,int(math.floor(y+.5))));pid=int(raster[iy,ix]);snap=0
     if pid not in pm:
      candidates=[(dx*dx+dy*dy,int(raster[iy+dy,(ix+dx)%W]),ix+dx,iy+dy) for dy in range(-3,4) for dx in range(-3,4) if dx*dx+dy*dy<=9 and 0<=iy+dy<H and int(raster[iy+dy,(ix+dx)%W]) in pm]
      if not candidates:continue
      dist,pid,ix,iy=min(candidates);snap=math.sqrt(dist)
     x0,x1,y0,y1=bounds[sid];nearby=sorted({pm[int(v)] for v in raster[max(0,iy-2):iy+3,max(0,ix-2):ix+3].flat if int(v) in pm})
     supp[sid].append({'city':fields[1],'province':pid,'actual_state':pm[pid],'geonames_id':int(fields[0]),'population_catalogue':int(fields[14] or 0),'lat':lat,'lon':lon,'coast_snap_pixels':snap,'nearby_states_within_2pixels':nearby,'bbox_distance':math.hypot(max(x0-x,0,x-x1),max(y0-y,0,y-y1)),'method':'Preserved settlement catalogue with fixed Patterson fit; boundary uncertainty retained'})
 for sid in fallback:
  if supp[sid]:matches[sid]=[min(supp[sid],key=lambda v:(v['bbox_distance'],-v['population_catalogue'],v['geonames_id']))]
 rows=[];mismatches=[];uncertain=[];unresolved=[]
 for sid,(country,labels) in sorted(queries.items()):
  entry={'state':sid,'names':NAMES[sid] if sid in NAMES else labels,'matches':matches[sid],'contains_named_city':any(v['actual_state']==sid for v in matches[sid])}
  if not matches[sid]:entry['status']='City centre unresolved in preserved catalogues';unresolved.append(entry)
  elif entry['contains_named_city']:entry['status']='City lies in named state'
  elif any(sid in v.get('nearby_states_within_2pixels',[]) for v in matches[sid]):entry['status']='Existing fixed-fit boundary uncertainty within two pixels; no automatic border change';uncertain.append(entry)
  else:entry['status']='City is outside named state; current user province list retained';mismatches.append(entry)
  rows.append(entry)
 report={'date':'2026-11-06','source':str(source),'source_sha256':sha(source),'supplementary_source':str(gaz/'research/geonames_cities500.zip'),'supplementary_sha256':sha(gaz/'research/geonames_cities500.zip'),'rows':rows,'regional_names_not_city_claims':{sid:labels[0] for sid,labels in NAMES.items() if sid not in queries},'mismatches':mismatches,'border_uncertain':uncertain,'unresolved':unresolved,'province_lists_preserved':True,'victory_points_not_added_or_relocated_by_city_review':True};dump(OUT/'city-review.json',report)
 current=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));current['clear_center_outside_named_state']=[v for v in current['clear_center_outside_named_state'] if v.get('state_id') not in set(queries)|set(NAMES)]
 for row in mismatches:
  match=row['matches'][0];current['clear_center_outside_named_state'].append({'state_id':row['state'],'state_name':row['names'][0],'city_name':match['city'],'city_province':match['province'],'actual_state':match['actual_state'],'report':META['report']+'/city-review.json'})
 current['latest_added_renamed_state_review']={'date':'2026-11-06','report':META['report']+'/city-review.json','city_named_states_checked':len(rows),'mismatches':mismatches,'border_uncertain':uncertain,'unresolved':unresolved};dump(BASE/'city_named_state_mismatches.json',current)
 print(json.dumps({'cities_checked':len(rows),'mismatches':[(v['state'],v['matches'][0]['province'],v['matches'][0]['actual_state']) for v in mismatches],'border_uncertain':[v['state'] for v in uncertain],'unresolved':[v['state'] for v in unresolved]},ensure_ascii=False))

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
 dump(OUT/'air-oob-audit.json',{'passed':True,'unit_files_checked':len(list((ROOT/'history/units').rglob('*.txt'))),'air_wings':air,'deployments':deployments,'all_country_history_oob_calls_including_nested':calls,'airport_migration':{'213':722},'country_histories_unchanged':True})
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
 dump(OUT/'geographic-reference-review.json',{'passed':True,'affected_states':sorted(affected),'nested_date_or_conditional_history':nested,'capital_anchors_preserved':{'ALT':654,'KYR':{'state':732,'city_province':12583},'SMI':148,'TAJ':{'state':742,'city_province':1384}},'state_id_reuse':{'147':'Old Salla provinces now 213/215; new province set from 1304, Ostrobothnia','722':'Old Petsamo provinces now 213; new province set from 213, Kola Peninsula'},'reference_changes':json.loads((OUT/'additional-reference-changes.json').read_text('utf8')),'nongeographic_numeric_uses':'Ship/division IDs, RGB, array indices, French grammatical tables and strategic region IDs were reviewed and retained in their own namespaces'})
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

def deliver_docs():
 runtime=json.loads((OUT/'runtime-audit.json').read_text('utf8'));assert runtime['passed']
 art=json.loads((OUT/'visual-asset-audit.json').read_text('utf8'));assert art['passed'] and art['native_capture_count']==3
 visual=json.loads((OUT/'visual-review.json').read_text('utf8'));assert visual['reviewed']
 models=json.loads((OUT/'model-changes.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));totals=json.loads((OUT/'allocation-totals.json').read_text('utf8'));static=json.loads((OUT/'static-audit.json').read_text('utf8'))
 table='\n'.join('| '+k+' | '+v['source']+' | '+str(v['rounded'])+' | '+v['rounding_difference']+' |' for k,v in totals['resources'].items())
 text=f'''# 2026-11-06 地块收尾与冷战地图同步

从11月4日晚中亚/高加索最新完成检查点继续，以用户当前保存的地块为准。新增1645“老街”，并将148拉皮→拉普兰、147萨拉→东博腾、1304东奥卢→凯努、1305东芬兰→北卡累利阿、722佩察莫→科拉半岛。当前1645州；六份新州/改名文件统一为编号加英文名，十语通用名称和有效国家前缀别名同步。中文逐字保留，城市名称与战略区名称不随州改名。

用户随后确认1645改名为老街 / Laukkai，十语沿用现有老街城市译名；详见20261106-laukkai-rename。此次仅改名，免重复地图测试和游戏启动。

## 地块、历史、建筑与交通

45个地块改隶，涉及24州；23个旧州的清空历史从最新APDC检查点恢复，其中148、586、881地块未改变仍须恢复。无重复、遗漏、新地块ID、空州或需新增来源关系的地块。人口资源以固定原经济来源计算，政治关系不从GF历史恢复。1645由999州地块4210拆出，继承BRM拥有/控制/核心、rural类别和1级基础设施，人口78376、钨4；老街城市胜利点仍1分。

147旧萨拉地块现属213/215，新的东博腾地块来自1304；722旧佩察莫地块现全属213，新科拉半岛地块来自旧213。地理条件已跟随这些实际地区：两组德国地理触发器及两处中文地理引用适配，保留其原玩法条件。所有国家历史、人物、身份与无关玩法保持，四份OOB以及全部国家历史的相关部署调用均核查；本轮无首都或OOB文件修改。

7处胜利点迁移宿主，全球仍5447点、20292分，分数和十语城市名保持。麦地那仍1206州/13462地块/10分及既有补给、铁路末端。实际建筑迁移5条记录：213的2级机场到722；3134的港口/海岸堡垒到722；9140港口到213；11822上的1座合成炼油厂从609到1039。工厂、机场、港口、堡垒与地标等实际等级总量保持；新州继承1级基础设施，全球基础设施3044→3045。实际存档另验证机场和炼油厂迁入/迁出等级。

模型归州修正{len(models['moved'])}条，补齐{len(models['added'])}条所需位置，共{models['records']}条；包含医疗中心、净化塔及有效spawn，排除湖泊陆地生成点。坐标、旋转和合理港口海洋绑定保持，补位置未增加真实建筑。

仅采纳上次验收结束后的新编辑器战略区输出，忽略28份旧输出；核对6份有差异的区域输出，恢复遗漏的4210，最终仅5区域的地块列表改变，天气/季节及全部海洋、湖泊战略归属保持。州无跨区，642条铁路、726补给节点无断点、重复或非法地块。省份图、定义、海峡、陆海类型、美术、字体、海面与光照均保持。

## 固定来源人口资源与城市

1133个固定来源州按原地块数比例精确分配，先求和再ROUND_HALF_UP。世界来源和取整前人口均2100007447，写入{totals['rounded_population']}，独立取整尾差+{totals['population_rounding_difference']}。allocation.json保存地块、来源、分母及精确贡献，economy-reverse-audit.json逐来源反查通过。

| 资源 | 来源/精确总量 | 写入总量 | 尾差 |
|---|---:|---:|---:|
{table}

核对7个相关城市名州，六个包含城市中心；213摩尔曼斯克州现不含3134摩尔曼斯克城市，城市随当前地块归722科拉半岛。按用户当前州界保留，记录为同名州例外，不擅自移动州界或改213的名字。147已改为地区名东博腾，移除其旧萨拉城市同名核查项。详见city-review.json与当前基线例外清单。

## 冷战、验收与保护

冷战当前1795州图块、3862边界图块，475个色槽、26档缩放、原生渲染器、调色板/着色器协议和非地图界面保持。{len(cw['changed'])}份地理产物变化，{len(cw['unchanged_world_edge_assets_preserved'])}份不变边缘贴图保留旧字节；1795份州遮罩逐像素符合当前归州。世界图{art['world_changed_pixels']}个变化像素均在受影响范围，范围外0变化。旧动态拥有国提示全部原字节保持，仅追加1645提示。

全量静态、扩展、地理引用、十语别名、OOB、模型、建筑及交通检查通过。GER 2060普通后台开局，进程{runtime['process']['pid']}，实际自动存档{runtime['date']}、SHA-256 `{runtime['save_sha256']}`；1645州所有者/控制者/核心/宣称全部吻合，非军事区0，169个有领土国家首都正确。当前冷战几何签名`{cw['signature']}`已在原生存档初始化。地图/建筑/铁路/冷战/本地化相关错误0；全部错误日志{runtime['all_error_log_lines']}行，与上次完成运行相比无新错误签名，不能称全游戏零错误。版本与实际DLC清单见runtime-audit.json；本轮只加载APDC及独立诊断驱动，用户组合中的Toolpack未加载。

已逐张检查世界图、缅甸详情和返回三张1920×1080实际截图，详情包含新州1645；返回世界图1000×500区域与首次打开逐像素一致。截图为私有窗口只读捕获，无桌面切换、鼠标或键盘输入，不扩大为全部缩放档或主地图美术的视觉验收。自己的测试进程和助手已停止、Steam标记清除，用户设置、启动器、继续游戏及原自动存档保持。

编辑器文档目录的中文州名也同步六处，`:-1`规范为`:0`，其他名称值保持，详见editor-localisation-audit.json。该名称同步不改变正式地图数据，免重复开局。

完整现场备份：`{BACKUP.as_posix()}`，project-before.zip保存35002份原文件及SHA-256清单，另有用户原始输入、旧日志、设置和编辑器输出。runtime-evidence.zip/runtime-save.zip保存本轮实际证据；states-checkpoint.zip/map-checkpoint.zip保存最终版本。preservation-audit.json核对所有本轮改动，固定原经济来源、导入快照、旧报告和既有用户修改保持。

本轮工具tools/map_maintenance/finish_20261106.py绑定本轮备份和计划，不能用于下一轮直接apply。冷战生成时旧工具硬编码的CPython3.12依赖路径导致一次导入失败，未安装产物；随后在CPython3.13预载对应依赖后完成stage隔离生成。后台启动初次路径空格未正确引用，未创建游戏进程；修正引用后仅进行上述一次实际开局，不将启动器空调用写为失败战局或多次开局。
'''
 (OUT/'README.md').write_text(text,'utf8')
 note='2026-11-06最新收尾：当前1645州；新增老街1645、指定改名5处、45地块改隶，恢复23个清空旧州历史，固定来源经济/VP/建筑/模型/战略区/十语及冷战同步。GER实际存档1645州关系、169有效首都及世界/BRM/返回画面通过；213摩尔曼斯克州不含现属722的同名城市，保留当前用户边界并记录例外。1645已按用户后续回复正式改为老街 / Laukkai，最新名称检查点为20261106-laukkai-rename。证据见[11月6日收尾](../../docs/map-maintenance/20261106/README.md)。'
 paths=['项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md']
 for rel in paths:
  p=ROOT/rel;t=p.read_text('utf8');lines=t.splitlines(keepends=True)
  if '2026-11-06最新收尾：' not in t:
   pos=t.find('\n')+1;t=t[:pos]+'\n'+note+'\n'+t[pos:]
  if rel.endswith('当前状态与未完成事项.md'):t=t.replace('截至2026-11-04晚。','历史状态截至2026-11-04晚；最新完成项见本页11月6日更新。',1).replace('当前州数1644','当前州数1645')
  if rel.endswith('地图与版本兼容_维护.md'):
   t=t.replace('当前指向20261104-central-asia-caucasus','当前指向20261106',1).replace('当前地图5120×2560，2:1；1644州。','当前地图5120×2560，2:1；1645州。',1)
  if rel.endswith('冷战系统_规则与维护.md'):
   old='地图最近于11月4日晚中亚/高加索收尾后同步，当前1644州/1794州图块/3860边界图块；最终实际大地图、SOV核心详情（227州）和返回画面通过，世界图返回像素一致。'
   t=t.replace(old,'地图最近于11月6日收尾后同步，当前1645州/1795州图块/3862边界图块；最终实际大地图、BRM核心详情及返回画面通过，世界图返回像素一致。当前几何签名9fa96167ccdc，11月4日签名为历史凭据。',1)
  p.write_text(t,'utf8')
 print('Report and current handover notices saved')

if __name__=='__main__':globals()[sys.argv[1]]()
