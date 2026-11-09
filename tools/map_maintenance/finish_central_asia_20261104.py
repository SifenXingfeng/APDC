"""Central Asia/Caucasus closeout against the latest completed APDC checkpoint.

Date-specific inputs; immutable source economy; no GF political replay. The
reviewed migration/model/name functions are reused with this run's configuration.
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
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-central-asia-20261104.json').read_text('utf8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];QA=Path(META['qa'])
NAMES={
1629:['北哈萨克','North Kazakhstan','Северный Казахстан','北カザフスタン','북카자흐스탄'],
1630:['费尔干纳','Fergana','Фергана','フェルガナ','페르가나'],
1631:['卡什卡达里亚','Qashqadaryo','Кашкадарья','カシュカダリヤ','카슈카다리야'],
1632:['吉扎克','Jizzakh','Джизак','ジザフ','지자흐'],
1633:['马雷','Mary','Мары','マル','마리'],
1634:['列巴普','Lebap','Лебап','レバプ','레바프'],
1635:['索格特','Sughd','Согд','ソグド','수그드'],
1636:['哈特隆','Khatlon','Хатлон','ハトロン','하틀론'],
1637:['东奥什','East Osh','Восточный Ош','東オシ','동오시'],
1638:['伊塞克湖','Issyk-Kul','Иссык-Куль','イシク・クル','이식쿨'],
1639:['纳伦','Naryn','Нарын','ナルイン','나린'],
1640:['贾拉拉巴德','Jalal-Abad','Джалал-Абад','ジャララバード','잘랄아바트'],
1641:['纳希切万','Nakhchivan','Нахичевань','ナヒチェヴァン','나히체반'],
1642:['纳卡','Nagorno-Karabakh','Нагорный Карабах','ナゴルノ・カラバフ','나고르노카라바흐'],
1643:['阿扎尔','Adjara','Аджария','アジャリア','아자리야'],
1644:['南奥塞梯','South Ossetia','Южная Осетия','南オセチア','남오세티야'],
589:['阿拉木图','Almaty','Алматы','アルマトイ','알마티'],
586:['江布尔','Jambyl','Жамбыл','ジャンブール','잠빌'],
590:['阿克莫拉','Akmola','Акмола','アクモラ','아크몰라'],
402:['阿克托','Aktobe','Актобе','アクトベ','악퇴베'],
407:['西哈萨克','West Kazakhstan','Западный Казахстан','西カザフスタン','서카자흐스탄'],
406:['阿特劳','Atyrau','Атырау','アティラウ','아티라우'],
587:['曼吉斯套','Mangystau','Мангистау','マングスタウ','망기스타우'],
831:['巴尔坎','Balkan','Балкан','バルカン','발칸'],
584:['阿哈尔','Ahal','Ахал','アハル','아할'],
742:['杜尚别','Dushanbe','Душанбе','ドゥシャンベ','두샨베'],
1147:['戈尔诺-巴达赫尚','Gorno-Badakhshan','Горно-Бадахшан','ゴルノ・バダフシャン','고르노바다흐샨'],
1148:['西奥什','West Osh','Западный Ош','西オシ','서오시'],
732:['楚河','Chui','Чуй','チュイ','추이']}
for module in [oldtool,oldverify]:
 module.META=META;module.BACKUP=BACKUP;module.OUT=OUT;module.QA=QA;module.NAMES=NAMES
original_update_references=oldtool.update_references

def plan():
 ss=statefiles(ROOT/'history/states');old=previous();op=pmap(old);pm=pmap(ss)
 assert set(ss)-set(old)==set(range(1629,1645));assert set(pm)==set(op),'Unknown or missing source provinces need explicit relationships'
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

def update_references(airport_moves,pm,old,affected):
 original_update_references(airport_moves,pm,old,affected)
 changes=json.loads((OUT/'geographic-reference-changes.json').read_text('utf8'))
 # Keep the actual pre-split capital cities, including releasable identities.
 anchors={'ARM':12320,'AZR':7661,'BUK':18684,'GEO':1599,'KAZ':1591,'KHI':1493,'KKP':1614,'KYR':12583,'TAJ':1384,'TMS':12333,'UZB':1459}
 for p in (ROOT/'history/countries').glob('*.txt'):
  tag=p.name[:3]
  if tag not in anchors:continue
  t=p.read_text('utf-8-sig');caps=[n for n in parse(t) if n.key=='capital'];assert len(caps)==1;cap=caps[0];pid=anchors[tag]
  if int(cap.value) not in affected:continue
  assert int(cap.value) in old and pid in {int(v.key) for v in old[int(cap.value)][2].get('provinces').children}
  if int(cap.value)==pm[pid]:continue
  changes.append({'file':p.relative_to(ROOT).as_posix(),'kind':'capital','tag':tag,'province':pid,'from':int(cap.value),'to':pm[pid],'reason':'Keep existing actual capital city after subdivision'});p.write_text(patches(t,[(cap.value_start,cap.value_end,str(pm[pid]))]),'utf8')
 dump(OUT/'geographic-reference-changes.json',changes)

def apply():
 assert json.loads((OUT/'plan.json').read_text('utf8'))['new_states']==list(range(1629,1645))
 oldtool.update_references=update_references
 oldtool.apply()
 dump(OUT/'name-decisions.json',{'names':{s:dict(zip(['simp_chinese','english','russian','japanese','korean'],v)) for s,v in NAMES.items()},'chinese_names':'User supplied; preserved verbatim, including 402 阿克托 and 1643 阿扎尔. City VP names are unchanged.','other_scripts':'Russian/Japanese/Korean modern names or project transliterations; other Latin languages use the verified modern spelling.','sources':{'Kazakhstan regions':'https://stat.gov.kz/en/industries/social-statistics/demography/publications/476649/','Kazakhstan Jambyl variant':'https://kazakhstan.travel/en/regions','Uzbekistan regional departments':'https://gov.uz/en/kadastr/departments/regional','Qashqadaryo variant':'https://api-portal.gov.uz/uploads/178/2026/03/18/9f41e440-b99c-5f71-b6f4-8e707698b480_media_.pdf','Jizzakh':'https://gov.uz/en/jizzax/guides','Turkmenistan regions':'https://editor.stat.gov.tm/en/contact-us','Tajikistan regions':'https://www.stat.tj/wp-content/uploads/2025/06/2023-tjdhs-final-report-en-final.pdf','Kyrgyzstan regions':'https://stat.gov.kg/en/opendata/category/39/','Adjara':'https://ajara.gov.ge/en','Caucasus geographical names':'https://www.europarl.europa.eu/RegData/etudes/BRIE/2017/599418/EPRS_BRI%282017%29599418_EN.pdf'},'source_scope':'Names only; project territory, cores and country identity follow the current APDC checkpoint and user province lists.'})

def references_apply():
 plan=json.loads((OUT/'plan.json').read_text('utf8'));primary={int(s):min(map(int,c),key=lambda k:(-c[str(k)],k)) for s,c in plan['state_sources'].items() if int(s)>=1629};p=ROOT/'common/scripted_triggers/GER_scripted_triggers.txt';t=p.read_text('utf8');edits=[];changes=[]
 for top in parse(t):
  if not(top.key.startswith('GER_is_') and top.key.endswith('_state')):continue
  blocks=[n for n in top.children if n.key=='OR']
  if len(blocks)!=1:continue
  block=blocks[0];members={int(n.value) for n in block.children if n.key=='state' and n.value and n.value.isdigit()};added=sorted(s for s,src in primary.items() if src in members and s not in members)
  if not added:continue
  last=[n for n in block.children if n.key=='state'][-1];end=t.find('\n',last.end);assert end>=0;edits.append((end,end,''.join('\n\t\tstate = '+str(s) for s in added)));changes.append({'file':p.relative_to(ROOT).as_posix(),'group':top.key,'added':added,'primary_sources':{s:primary[s] for s in added}})
 if edits:p.write_text(patches(t,edits),'utf8')
 dump(OUT/'additional-reference-changes.json',changes);print(json.dumps({'geographic_groups_changed':len(changes),'new_group_members':sum(len(v['added']) for v in changes)}))

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
 dump(OUT/'extended-static-audit.json',{'passed':True,'all_registered_political_tags':True,'inactive_core_claim_cleanup_verified':True,'affected_province_spawn_coverage':True,'nongeographic_existing_histories_preserved':sorted(preserved),'recorded_capacity_exception':'capacity-adjustments.json: state 589 adds exactly one shared slot' if (OUT/'capacity-adjustments.json').exists() else None,'nested_affected_date_or_conditional_history':nested,'country_capital_only_change':'KAZ','unrelated_gameplay_directories_byte_preserved':True,'fixed_sources_reverse_checked':len(reverse),'sea_connectivity':'Province pixels, sea/lake region assignments and sea adjacencies unchanged from completed checkpoint'})
 print('Extended Central Asia static audit passed')

def preservation():
 from concurrent.futures import ThreadPoolExecutor
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'));plan=json.loads((OUT/'plan.json').read_text('utf8'));renames=json.loads((OUT/'renames.json').read_text('utf8'));loc=json.loads((OUT/'localisation-changes.json').read_text('utf8'));ss=statefiles(ROOT/'history/states')
 allowed={v['file'] for v in cw['changed']}|{v['file'] for v in loc}|{v['new'] for v in renames}|{ss[s][0].relative_to(ROOT).as_posix() for s in plan['affected_states']}
 allowed|={v['file'] for v in json.loads((OUT/'geographic-reference-changes.json').read_text('utf8'))+json.loads((OUT/'additional-reference-changes.json').read_text('utf8'))}
 regions=json.loads((OUT/'strategic-repairs.json').read_text('utf8'))['written_regions'];allowed|={p.relative_to(ROOT).as_posix() for p in (ROOT/'map/strategicregions').glob('*.txt') if int(parse(p.read_text('utf-8-sig'))[0].val('id')) in regions}
 allowed|={'map/buildings.txt','tools/map_maintenance/finish_central_asia_20261104.py','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json','tools/map_maintenance/baseline/latest_checkpoint.json'}
 allowed|={'项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md'}
 files=[]
 for folder,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in ['.git','__pycache__']];files.extend(Path(folder)/n for n in names if Path(folder)/n!=OUT/'preservation-audit.json')
 def inspect(p):return p.relative_to(ROOT).as_posix(),sha(p)
 with ThreadPoolExecutor(max_workers=6) as pool:after=dict(pool.map(inspect,files))
 changes=[{'file':p,'before':before.get(p,{}).get('sha256'),'after':h} for p,h in after.items() if h!=before.get(p,{}).get('sha256')];removed=[p for p in before if not (ROOT/p).is_file()];unexpected=[v for v in changes if v['file'] not in allowed and not v['file'].startswith(META['report']+'/')];unexpected_removed=sorted(set(removed)-{v['old'] for v in renames})
 fixed=[p for p in before if p.startswith(('tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_'))];assert all(after[p]==before[p]['sha256'] for p in fixed)
 report={'passed':not(unexpected or unexpected_removed),'files_before':len(before),'files_after':len(after),'changed_or_added':changes,'authorized_rename_removals':removed,'unexpected_removed':unexpected_removed,'unexpected_changes':unexpected,'fixed_economy_and_imported_snapshots_byte_preserved':True,'all_other_preexisting_user_changes_preserved':True};dump(OUT/'preservation-audit.json',report);assert report['passed'],{'unexpected':unexpected,'removed':unexpected_removed};dump(BACKUP/'final-file-manifest.json',{p:{'sha256':h} for p,h in after.items()});print(json.dumps({'preserved':True,'changed_or_added':len(changes),'renamed':len(removed),'files_checked':len(after)}))

# The full audit, isolated runtime, geometry review and checkpoint functions below
# are copied from the reviewed previous tools, with this run's counts and markers.

def audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pstate=pmap(states);defs,raster=raster_data();H,W=raster.shape;issues=[]
 assert len(states)==1644 and set(range(1,1645))==set(states)
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
  for sid in NAMES:assert d['STATE_'+str(sid)]==NAMES[sid][{'simp_chinese':0,'russian':2,'japanese':3,'korean':4}.get(lang,1)]
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
 (QA/'mod/APDC_CentralAsiaQA.mod').write_text('name="APDC Central Asia diagnostics"\npath="'+(QA/'driver').as_posix()+'"\nsupported_version="1.19.*"\n','utf8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_CentralAsiaQA.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA_20261104/settings.txt').read_text('utf8');(QA/'settings.txt').write_text(settings,'utf8')
 (QA/'driver/common/defines/zzzz_APDC_city_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf8')
 pol=json.loads((BASE/'initial_territories.json').read_text('utf8'));checks=''
 for sid in sorted(set(json.loads((OUT/'plan.json').read_text('utf8'))['affected_states'])):
  p=pol[str(sid)];test=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+v for v in p['cores']);checks+=f'{sid} = {{ if = {{ limit = {{ {test} }} log = "APDC_CA_20261104 PASS state_{sid}" }} else = {{ log = "APDC_CA_20261104 FAIL state_{sid}" }} }}\n'
 daily='add_to_variable = { apdc_qa_city_day = 1 }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 1 } } '+checks+'apdc_cw_open_panel = yes log = "APDC_CA_20261104 WORLD_READY" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 20 } } set_variable = { apdc_cw_selected = SOV } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_CA_20261104 SOV_DETAIL_READY states=[?apdc_cw_detail_state_count]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_city_day = 34 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_CA_20261104 WORLD_RETURNED" }\nlog = "APDC_CA_20261104 DAY [?apdc_qa_city_day] date=[GetDateText]"\n'
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
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[v for v in game.splitlines() if 'APDC_CA_20261104' in v]
 relevant=[v for v in error.splitlines() if re.search(r'MAP_ERROR|map/buildings.txt|Province with id:|State \d+ has no|[Rr]ailway|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect|pdx_localize.cpp|localization.*error',v)]
 with zipfile.ZipFile(Path(META['checkpoint']['backup'])/'runtime-evidence.zip') as z:prior=z.read('logs/error.log').decode('utf-8-sig',errors='replace')
 norm=lambda s:re.sub(r'^(?:\[[^\]]*\])+\s*','',s)
 new=collections.Counter(norm(s) for s in error.splitlines())-collections.Counter(norm(s) for s in prior.splitlines());changed=[p for p,h in META['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1];markers=['WORLD_READY','SOV_DETAIL_READY','WORLD_RETURNED']
 signature=json.loads((OUT/'cold-war-refresh.json').read_text('utf8'))['signature'];geometry_flag='apdc_cw_render_lookup_v2_geo_'+signature;assert geometry_flag in text,'Native save did not initialize the current geography lookup'
 capacity={'extra_shared_slots':int(native[589].val('extra_shared_slots','0')),'industrial_complex':int(native[589].get('buildings').get('industrial_complex').val('level'))}
 assert capacity['extra_shared_slots']==1 and capacity['industrial_complex']>=2,capacity
 passed=not(differences or dmz or relevant or changed or new) and 'FAIL' not in '\n'.join(evidence) and all(any(marker in line for line in evidence) for marker in markers) and date.startswith('2060.2.') and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers'])
 system=(QA/'logs/system.log').read_text('utf-8-sig',errors='replace');report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'relation_differences':differences,'initial_dmz':dmz,'active_capitals_checked':len(capitals),'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'new_error_signatures_vs_last_completed_runtime':dict(new),'user_file_changes':changed,'evidence':evidence,'process':record,'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf8')),'version_and_active_dlcs':[s for s in system.splitlines() if 'Version:' in s or 'Active DLC' in s],'input_desktop_switched':False,'mouse_keyboard_sent':False}
 dump(OUT/'runtime-audit.json',report)
 report['current_geography_lookup_flag_in_native_save']=geometry_flag;report['state_589_capacity']=capacity;dump(OUT/'runtime-audit.json',report)
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
  rel='localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml';loc_before=z.read(rel);loc_after=(ROOT/rel).read_bytes();assert loc_after.startswith(loc_before);assert set(re.findall(rb'APDC_CW_STATE_(\d+)',loc_after[len(loc_before):]))=={str(s).encode() for s in range(1629,1645)}
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
 cp={**META['checkpoint'],'date':'2026-11-04','report':META['report'],'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER '+json.loads((OUT/'runtime-audit.json').read_text('utf8'))['date']+'; all 1644 state relations checked; world/SOV/return reviewed; own game/helpers stopped','runtime_report':META['report']+'/runtime-audit.json','visual_report':META['report']+'/visual-review.json','backup':str(BACKUP),'geography_backup':str(BACKUP),'previous_report':META['checkpoint']['report'],'map_checkpoint_archive':ma.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(ma),'states':len(ss),'city_review':META['report']+'/city-review.json'}
 dump(BASE/'latest_checkpoint.json',cp);preservation();print('Central Asia checkpoint saved')

def repair_capacity():
 assert not (OUT/'capacity-adjustments.json').exists(),'Capacity repair is a one-time reviewed adjustment'
 failed=json.loads((OUT/'runtime-before-capacity-fix.json').read_text('utf8'));assert len(failed['new_error_signatures_vs_last_completed_runtime'])==1
 p=ROOT/'history/states/589-Almaty.txt';raw=p.read_bytes();t=raw.decode('utf8');s=parse(t)[0];h=s.get('history');assert s.val('state_category')=='pastoral' and h.get('buildings').val('industrial_complex')=='2' and not h.get('add_extra_state_shared_building_slots')
 (BACKUP/'589-Almaty-before-capacity-fix.txt').write_bytes(raw);v=h.get('victory_points');p.write_text(patches(t,[(v.start,v.start,'add_extra_state_shared_building_slots = 1\n\t\t')]),'utf8')
 dump(OUT/'capacity-adjustments.json',{'state':589,'category_preserved':'pastoral','industrial_complex_before':2,'industrial_complex_after':2,'extra_shared_slots_added':1,'reason':'Actual engine reported one slot of overflow after a preserved existing factory migrated into this state. Add exactly the space needed to retain it; no new factory or category change.','source_before_sha256':hashlib.sha256(raw).hexdigest(),'source_after_sha256':sha(p),'first_run_report':'runtime-before-capacity-fix.json','first_run_evidence_archive':str(BACKUP/'runtime-before-capacity-fix.zip')})
 print('Added one shared slot to hold the two preserved factories in Almaty 589')

def city_review():
 import unicodedata
 import numpy as np
 def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
 source=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/GF-MAP/.codex_backups/20261020-183551-chinese-city-name-corrections/现代胜利点总表.json');catalog=json.loads(source.read_text('utf-8-sig'));ss=statefiles(ROOT/'history/states');pm=pmap(ss)
 queries={1630:('UZ',['Fergana','Fargona']),1632:('UZ',['Jizzakh','Jizzax']),1633:('TM',['Mary']),1639:('KG',['Naryn']),1640:('KG',['Jalal-Abad','Manas']),1641:('AZ',['Nakhchivan','Naxcivan']),589:('KZ',['Almaty']),402:('KZ',['Aktobe','Aqtobe']),406:('KZ',['Atyrau']),742:('TJ',['Dushanbe']),405:('UZ',['Tashkent']),404:('KZ',['Kyzylorda']),585:('UZ',['Navoiy','Navoi']),588:('KZ',['Semipalatinsk','Semey']),882:('KZ',['Pavlodar']),830:('UZ',['Bukhara']),832:('TM',['Dashoguz','Dasoguz']),575:('RU',['Mirny','Mirnyy']),1592:('RU',['Lensk'])}
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
 report={'date':'2026-11-04','source':str(source),'source_sha256':sha(source),'supplementary_source':str(gaz/'research/geonames_cities500.zip'),'supplementary_sha256':sha(gaz/'research/geonames_cities500.zip'),'rows':rows,'regional_names_not_city_claims':{sid:labels[0] for sid,labels in NAMES.items() if sid not in queries},'mismatches':mismatches,'border_uncertain':uncertain,'unresolved':unresolved,'province_lists_preserved':True,'victory_points_not_added_or_relocated_by_city_review':True,'overridden_prior_alignment':'Current user-saved province 10557 is back in 1592. Do not replay the preceding alignment request over this new map.'};dump(OUT/'city-review.json',report)
 current=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));current['clear_center_outside_named_state']=[v for v in current['clear_center_outside_named_state'] if v.get('state_id') not in queries]
 for row in mismatches:
  match=row['matches'][0];current['clear_center_outside_named_state'].append({'state_id':row['state'],'state_name':row['names'][0],'city_name':match['city'],'city_province':match['province'],'actual_state':match['actual_state'],'report':META['report']+'/city-review.json'})
 current['latest_added_renamed_state_review']={'date':'2026-11-04','report':META['report']+'/city-review.json','city_named_states_checked':len(rows),'mismatches':mismatches,'border_uncertain':uncertain,'unresolved':unresolved};dump(BASE/'city_named_state_mismatches.json',current)
 print(json.dumps({'cities_checked':len(rows),'mismatches':[(v['state'],v['matches'][0]['province'],v['matches'][0]['actual_state']) for v in mismatches],'border_uncertain':[v['state'] for v in uncertain],'unresolved':[v['state'] for v in unresolved]},ensure_ascii=False))

if __name__=='__main__':globals()[sys.argv[1]]()
