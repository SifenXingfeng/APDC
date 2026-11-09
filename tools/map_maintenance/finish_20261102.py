"""November 2 India state split: reviewed inputs, current APDC checkpoint, scoped writes.

Commands: plan, apply, audit, prepare_qa, runtime_audit, checkpoint.
This date-specific migration must not be replayed against a later project.
"""
from pathlib import Path
import sys,json,hashlib,zipfile,collections,csv,re,io,math,os,shutil
from fractions import Fraction
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,walk,patches
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-map-finish-20261102.json').read_text('utf-8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];BASE=ROOT/'tools/map_maintenance/baseline'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
USER=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
LANGS=['simp_chinese','english','french','german','spanish','braz_por','polish','russian','japanese','korean']
# 中文逐字依用户；1562按后续确认写全称。英文用于正式文件名。
NAMES={
1559:('恰尔肯德','Jharkhand','Джаркханд','ジャールカンド','자르칸드'),
1560:('新德里','New Delhi','Нью-Дели','ニューデリー','뉴델리'),
1561:('锡尔萨','Sirsa','Сирса','シルサ','시르사'),
1562:('拉夫沙漠','Thar Desert','Пустыня Тар','タール砂漠','타르 사막'),
1563:('卡提阿瓦','Kathiawar','Катхиявар','カーティヤーワール','카티아와르'),
1564:('巴尔梅尔','Barmer','Бармер','バールメール','바르메르'),
1565:('乌代布尔','Udaipur','Удайпур','ウダイプル','우다이푸르'),
1566:('锡尔瓦萨','Silvassa','Силвасса','シルヴァーサー','실바사'),
1567:('科塔','Kota','Кота','コーター','코타'),
1568:('瑟德纳','Satna','Сатна','サトナー','사트나'),
1569:('阿里格尔','Aligarh','Алигарх','アリーガル','알리가르'),
1570:('伯尔珀尼','Parbhani','Парбхани','パルバニー','파르바니'),
1571:('德干','Deccan','Декан','デカン','데칸'),
1572:('希莫加','Shivamogga','Шивамогга','シヴァモッガ','시바모가'),
1573:('拉克沙群岛','Lakshadweep','Лакшадвип','ラクシャドウィープ','락샤드위프'),
1574:('代利杰里','Thalassery','Талассери','タラセリー','탈라세리'),
1575:('海得拉巴','Hyderabad','Хайдарабад','ハイデラバード','하이데라바드'),
1576:('卡基纳达','Kakinada','Какинада','カキナダ','카키나다'),
1577:('南巴斯塔','South Bastar','Южный Бастар','南バスター','남바스타르'),
1578:('南奥里萨','South Odisha','Южная Одиша','南オディシャ','남오디샤'),
1145:('喜马偕尔','Himachal Pradesh','Химачал-Прадеш','ヒマーチャル・プラデーシュ','히마찰프라데시'),
1144:('北阿坎德','Uttarakhand','Уттаракханд','ウッタラーカンド','우타라칸드'),
986:('旁遮普','Punjab','Пенджаб','パンジャーブ','펀자브'),
439:('哈里亚纳','Haryana','Харьяна','ハリヤーナー','하리아나'),
433:('斋浦尔','Jaipur','Джайпур','ジャイプル','자이푸르'),
428:('甘地讷格尔','Gandhinagar','Гандинагар','ガンディーナガル','간디나가르'),
437:('乌贾因','Ujjain','Удджайн','ウッジャイン','우자인'),
436:('博帕尔','Bhopal','Бхопал','ボーパール','보팔'),
438:('勒克瑙','Lucknow','Лакхнау','ラクナウ','러크나우'),
983:('伊切尔格伦吉','Ichalkaranji','Ичалкаранджи','イチャルカランジ','이찰카란지'),
427:('钱德拉布尔','Chandrapur','Чандрапур','チャンドラプル','찬드라푸르'),
425:('班加罗尔','Bengaluru','Бангалор','ベンガルール','벵갈루루'),
982:('特里凡得琅','Thiruvananthapuram','Тируванантапурам','ティルヴァナンタプラム','티루바난타푸람'),
320:('拉杰巴莱亚姆','Rajapalayam','Раджапалаям','ラージャパーラヤム','라자팔라얌'),
423:('金奈','Chennai','Ченнаи','チェンナイ','첸나이'),
424:('内洛尔','Nellore','Неллор','ネルール','넬로르'),
}

def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(n):return (n.key,n.value,n.op,tuple(canon(c) for c in n.children))
def statefiles(folder):
 out={}
 for p in sorted(folder.glob('*.txt')):
  t=p.read_text('utf-8-sig');n=next(n for n in parse(t) if n.key=='state');sid=int(n.val('id'));assert sid not in out;out[sid]=(p,t,n)
 return out
def previous():
 cp=json.loads((BACKUP/'initial-scan.json').read_text('utf-8'))['checkpoint'];out={}
 with zipfile.ZipFile(ROOT/cp['state_history_archive']) as z:
  for name in z.namelist():
   if name.endswith('.txt'):
    t=z.read(name).decode('utf-8-sig');n=parse(t)[0];out[int(n.val('id'))]=(ROOT/'history/states'/Path(name).name,t,n)
 return out
def pmap(states):
 out={}
 for sid,(_,_,s) in states.items():
  for n in s.get('provinces').children:
   pid=int(n.key);assert pid not in out,('duplicate province',pid,sid,out.get(pid));out[pid]=sid
 return out
def resolved_states():
 states=statefiles(ROOT/'history/states')
 for sid in [436,437]:
  p,t,s=states[sid];n=s.get('provinces');ids=list(dict.fromkeys(int(x.key) for x in n.children));ids=[x for x in ids if x!=(18987 if sid==436 else 10816)]
  t=patches(t,[(n.value_start,n.value_end,'{\n\t\t'+' '.join(map(str,ids))+'\n\t}')]);states[sid]=(p,t,parse(t)[0])
 return states
def allocation(states):
 originals=statefiles(BASE/'original_economy/history/states');source=pmap(originals);values={}
 for sid,(_,_,s) in originals.items():
  res={}
  for b in [n for n in s.children if n.key=='resources']:
   for n in b.children:assert n.key not in res;res[n.key]=Fraction(n.value)
  values[sid]=(int(s.val('manpower','0')),res,len(s.get('provinces').children))
 out={};coverage=collections.Counter()
 for sid,(_,_,s) in states.items():
  groups=collections.defaultdict(list)
  for n in s.get('provinces').children:pid=int(n.key);assert pid in source,('new province needs source',pid);groups[source[pid]].append(pid);coverage[pid]+=1
  pop=Fraction();res=collections.defaultdict(Fraction);parts=[]
  for src,pids in sorted(groups.items()):
   v,r,d=values[src];f=Fraction(len(pids),d);pop+=v*f
   for k,x in r.items():res[k]+=x*f
   parts.append({'source':src,'provinces':sorted(pids),'denominator':d,'source_population':v,'source_resources':{k:str(x) for k,x in r.items()},'population_contribution':str(v*f),'resource_contributions':{k:str(x*f) for k,x in r.items()}})
  half=lambda x:(2*x.numerator+x.denominator)//(2*x.denominator)
  out[sid]={'population':half(pop),'population_exact':str(pop),'resources':{k:half(v) for k,v in sorted(res.items()) if half(v)},'resources_exact':{k:str(v) for k,v in sorted(res.items())},'contributions':parts}
 assert set(coverage)==set(source) and set(coverage.values())=={1}
 source_pop=sum(x[0] for x in values.values());exact_pop=sum((Fraction(x['population_exact']) for x in out.values()),Fraction());assert source_pop==exact_pop
 totals={'source_population':source_pop,'exact_population':str(exact_pop),'rounded_population':sum(x['population'] for x in out.values()),'population_rounding_difference':sum(x['population'] for x in out.values())-source_pop,'resources':{}}
 for k in sorted({k for _,r,_ in values.values() for k in r}):
  src=sum((r.get(k,Fraction()) for _,r,_ in values.values()),Fraction());exact=sum((Fraction(x['resources_exact'].get(k,'0')) for x in out.values()),Fraction());rounded=sum(x['resources'].get(k,0) for x in out.values());assert src==exact
  totals['resources'][k]={'source':str(src),'exact':str(exact),'rounded':rounded,'rounding_difference':str(rounded-src)}
 return out,totals
def raster_data():
 import numpy as np
 from PIL import Image
 definitions={}
 for row in csv.reader((ROOT/'map/definition.csv').read_text('utf-8-sig').splitlines(),delimiter=';'):
  if row and row[0].isdigit():definitions[int(row[0])]={'rgb':tuple(map(int,row[1:4])),'type':row[4],'coastal':row[5]}
 lut=np.zeros(1<<24,np.uint16)
 for pid,d in definitions.items():r,g,b=d['rgb'];lut[r+(g<<8)+(b<<16)]=pid
 a=np.asarray(Image.open(ROOT/'map/provinces.bmp'),np.uint32);return definitions,lut[a[:,:,0]+(a[:,:,1]<<8)+(a[:,:,2]<<16)]
def plan():
 states=resolved_states();old=previous();op=pmap(old);np=pmap(states);a,totals=allocation(states)
 changes=[{'province':p,'from':op.get(p),'to':np.get(p)} for p in sorted(set(op)|set(np)) if op.get(p)!=np.get(p)]
 affected=sorted({v[k] for v in changes for k in ['from','to']})
 regions={};editor_changes=[]
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];regions[int(n.val('id'))]=(p,t,n)
 for p in (USER/'map/strategicregions').rglob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];rid=int(n.val('id'));oldp,oldt,oldn=regions[rid]
  oldlist=[int(x.key) for x in oldn.get('provinces').children];newlist=[int(x.key) for x in n.get('provinces').children]
  if oldlist!=newlist:
   editor_changes.append({'region':rid,'source':str(p),'removed':sorted(set(oldlist)-set(newlist)),'added':sorted(set(newlist)-set(oldlist))})
   replacement=patches(oldt,[(oldn.get('provinces').value_start,oldn.get('provinces').value_end,t[n.get('provinces').value_start:n.get('provinces').value_end])]);regions[rid]=(oldp,replacement,parse(replacement)[0])
 preg={};duplicates=[]
 for rid,(_,_,n) in regions.items():
  for x in n.get('provinces').children:
   pid=int(x.key)
   if pid in preg:duplicates.append([pid,preg[pid],rid])
   preg[pid]=rid
 cross=[{'state':sid,'regions':dict(collections.Counter(preg.get(int(x.key)) for x in s.get('provinces').children))} for sid,(_,_,s) in states.items() if len({preg.get(int(x.key)) for x in s.get('provinces').children})!=1]
 defs,raster=raster_data();H,W=raster.shape
 models=[];anchors=collections.defaultdict(list);wrong=[]
 for i,line in enumerate((ROOT/'map/buildings.txt').read_text('utf-8-sig').splitlines(),1):
  if not line.strip():continue
  row=line.split(';');assert len(row)==7,(i,line)
  sid=int(row[0]);x,z=math.floor(float(row[2])),math.floor(float(row[4]));pid=int(row[6]) if row[1]=='floating_harbor' else int(raster[H-1-z,x]);actual=np.get(pid)
  models.append({'row':row,'old_state':sid,'province':pid,'actual':actual,'line':i})
  if actual:anchors[sid,row[1]].append((actual,pid,i))
  if actual and actual!=sid:wrong.append({'line':i,'old':sid,'new':actual,'kind':row[1],'province':pid,'related':sid in affected or actual in affected})
 migrations=[]
 for sid,(_,t,s) in old.items():
  if sid not in affected:continue
  b=s.get('history').get('buildings')
  if b:
   for n in b.children:
    if n.key.isdigit():migrations.append({'from':sid,'to':np[int(n.key)],'province':int(n.key),'kind':'province_block','value':t[n.start:n.end]})
    elif n.key!='infrastructure':
     candidate=anchors.get((sid,n.key),[])
     migrations.append({'from':sid,'kind':n.key,'value':n.value,'targets':dict(collections.Counter(x[0] for x in candidate)),'first_anchor':candidate[0] if candidate else None})
 report={'checkpoint':json.loads((BACKUP/'initial-scan.json').read_text('utf-8'))['checkpoint'],'backup':str(BACKUP),'new_states':sorted(set(states)-set(old)),'affected_states':affected,'province_transfers':changes,'duplicate_resolution':{'10816':436,'18987':437,'within_state_duplicates_removed':3},'economy_totals':totals,'strategic_editor_changes':editor_changes,'strategic_duplicates':duplicates,'cross_region_states':cross,'model_state_mismatches':wrong,'actual_building_migration_candidates':migrations,'state_sources':{str(sid):dict(collections.Counter(op[int(x.key)] for x in states[sid][2].get('provinces').children)) for sid in affected}}
 OUT.mkdir(parents=True,exist_ok=True);dump(OUT/'plan.json',report);dump(OUT/'allocation.json',a);dump(OUT/'allocation-totals.json',totals)
 with zipfile.ZipFile(BACKUP/'strategic-plan.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p,t,n in regions.values():z.writestr(p.relative_to(ROOT).as_posix(),t.encode('utf-8'))
 print(json.dumps({'states':len(states),'transfers':len(changes),'affected_states':len(affected),'strategic_changed':[r['region'] for r in editor_changes],'cross_region_states':cross,'strategic_duplicates':duplicates,'building_candidates':migrations,'model_mismatches_related':sum(x['related'] for x in wrong),'totals':totals},ensure_ascii=False))

def set_field(t,s,key,value):
 n=s.get(key)
 return patches(t,[(n.value_start,n.value_end,value)]) if n else patches(t,[(s.value_end-1,s.value_end-1,'\t'+key+' = '+value+'\n')])

def apply():
 import numpy as np
 from PIL import Image
 states=resolved_states();old=previous();op=pmap(old);npmap=pmap(states);plan=json.loads((OUT/'plan.json').read_text('utf-8'));affected=set(plan['affected_states']);alloc,totals=allocation(states)
 # Use staged editor province lists; repair their omissions from the existing
 # region assignment, then put each state wholly in its majority region.
 original_regions={};regions={}
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];original_regions[int(n.val('id'))]=(p,t,n)
 with zipfile.ZipFile(BACKUP/'strategic-plan.zip') as z:
  for name in z.namelist():
   t=z.read(name).decode('utf-8');n=parse(t)[0];regions[int(n.val('id'))]=(ROOT/name,t,n)
 preg_old={int(v.key):rid for rid,(_,_,n) in original_regions.items() for v in n.get('provinces').children}
 preg={};region_lists={rid:list(dict.fromkeys(int(x.key) for x in n.get('provinces').children)) for rid,(_,_,n) in regions.items()}
 for rid,pids in region_lists.items():
  for pid in pids:assert pid not in preg,('different editor regions repeat',pid);preg[pid]=rid
 missing=sorted(set(preg_old)-set(preg));repairs=[]
 for pid in missing:preg[pid]=preg_old[pid];region_lists[preg_old[pid]].append(pid)
 for sid,(_,_,s) in states.items():
  pids=[int(n.key) for n in s.get('provinces').children];counts=collections.Counter(preg[p] for p in pids)
  if len(counts)>1:
   target=min(counts,key=lambda rid:(-counts[rid],rid))
   for pid in pids:
    if preg[pid]!=target:repairs.append({'state':sid,'province':pid,'from':preg[pid],'to':target});region_lists[preg[pid]].remove(pid);region_lists[target].append(pid);preg[pid]=target
 region_changes=[]
 for rid,(p,t,n) in regions.items():
  v=n.get('provinces');text=patches(t,[(v.value_start,v.value_end,'{\n\t\t'+' '.join(map(str,sorted(region_lists[rid])))+'\n\t}')])
  # Only province lists are written. Original weather and seasons remain exact.
  before=original_regions[rid][1];before_node=original_regions[rid][2];nb=parse(text)[0]
  assert [canon(x) for x in before_node.children if x.key!='provinces']==[canon(x) for x in nb.children if x.key!='provinces']
  if {int(x.key) for x in before_node.get('provinces').children}!=set(region_lists[rid]):p.write_text(text,'utf-8');region_changes.append(rid)
 dump(OUT/'strategic-repairs.json',{'missing_editor_provinces_restored':missing,'cross_state_repairs':repairs,'written_regions':region_changes,'weather_preserved':True})
 defs,raster=raster_data();H,W=raster.shape;oldmodels=[];anchors=collections.defaultdict(list)
 for line in (ROOT/'map/buildings.txt').read_text('utf-8-sig').splitlines():
  if not line.strip():continue
  row=line.split(';');sid=int(row[0]);x,z=math.floor(float(row[2])),math.floor(float(row[4]));pid=int(row[6]) if row[1]=='floating_harbor' else int(raster[H-1-z,x]);actual=npmap.get(pid)
  oldmodels.append((row,pid,actual));anchors[sid,row[1]].append((pid,actual))
 values=collections.defaultdict(collections.Counter);provbuild=collections.defaultdict(dict);vps=collections.defaultdict(list);building_moves=[];airport_moves={}
 for sid,(p,t,s) in old.items():
  if sid not in affected:continue
  h=s.get('history')
  assert not any(re.fullmatch(r'\d{4}\.\d+\.\d+',n.key) for n in walk(h.children)),('affected date history requires explicit relocation',sid)
  for v in [n for n in h.children if n.key=='victory_points']:
   items=[x.key for x in v.children]
   for pid,score in zip(items[::2],items[1::2]):vps[npmap[int(pid)]].append((int(pid),int(score)))
  b=h.get('buildings')
  if not b:continue
  for n in b.children:
   if n.key=='infrastructure':continue
   if n.key.isdigit():
    pid=int(n.key);target=npmap[pid];assert pid not in provbuild[target];provbuild[target][pid]=t[n.value_start:n.value_end]
    if target!=sid:building_moves.append({'from':sid,'to':target,'province':pid,'kind':'province_buildings'})
   else:
    assert n.value and n.value.isdigit(),('conditional state building requires review',sid,n.key)
    level=int(n.value);slots=anchors.get((sid,n.key),[])
    assert slots,('actual building missing model position',sid,n.key)
    for i in range(level):
     pid,target=slots[min(i,len(slots)-1)];assert target is not None;values[target][n.key]+=1
     if target!=sid:building_moves.append({'from':sid,'to':target,'province':pid,'kind':n.key,'level':1})
    if n.key=='air_base':
     targets={a[1] for a in slots};assert len(targets)==1;airport_moves[sid]=next(iter(targets))
 politics=json.loads((BASE/'initial_territories.json').read_text('utf-8'));active={v['owner'] for v in politics.values()};state_report=[];renames=[]
 for sid in sorted(affected|set(NAMES)):
  p,t,s=states[sid];sources=collections.Counter(op[int(v.key)] for v in s.get('provinces').children);primary=min(sources,key=lambda k:(-sources[k],k));source_h=old[primary][2].get('history')
  if sid in affected:
   owners={old[src][2].get('history').val('owner') for src in sources};controllers={old[src][2].get('history').val('controller',old[src][2].get('history').val('owner')) for src in sources};assert len(owners)==len(controllers)==1
   owner=next(iter(owners));controller=next(iter(controllers));cores={n.value.strip('"') for n in source_h.children if n.key=='add_core_of'};claims={n.value.strip('"') for n in source_h.children if n.key=='add_claim_by'}
   removed=[]
   if owner in cores:removed=sorted((cores|claims)-active);cores-=set(removed);claims-=set(removed)
   politics[str(sid)]={'owner':owner,'controller':controller,'cores':sorted(cores),'claims':sorted(claims)}
   h='history = {\n\t\towner = '+owner+'\n\t\tcontroller = '+controller+'\n'+''.join('\t\tadd_core_of = '+k+'\n' for k in sorted(cores))+''.join('\t\tadd_claim_by = '+k+'\n' for k in sorted(claims))
   # Retain non-geographic history of an existing state; geographical GDP
   # markers follow the source territory when a whole state ID is repurposed.
   base_h=old[sid][2].get('history') if sid in old else source_h;base_text=old[sid][1] if sid in old else old[primary][1]
   excluded={'owner','controller','add_core_of','add_claim_by','victory_points','buildings'}
   for n in base_h.children:
    if n.key not in excluded and not(n.key=='set_state_flag' and n.value.startswith('GDP_regions_')):h+='\t\t'+base_text[n.start:n.end]+'\n'
   for n in source_h.children:
    if n.key=='set_state_flag' and n.value.startswith('GDP_regions_'):h+='\t\t'+old[primary][1][n.start:n.end]+'\n'
   for pid,score in sorted(vps[sid]):h+=f'\t\tvictory_points = {{ {pid} {score} }}\n'
   infra=source_h.get('buildings').val('infrastructure','0') if source_h.get('buildings') else '0'
   h+='\t\tbuildings = {\n\t\t\tinfrastructure = '+infra+'\n'+''.join(f'\t\t\t{k} = {v}\n' for k,v in sorted(values[sid].items()))+''.join(f'\t\t\t{pid} = '+value+'\n' for pid,value in sorted(provbuild[sid].items()))+'\t\t}\n\t}'
   n=s.get('history');t=patches(t,[(n.start,n.end,h)]) if n else patches(t,[(s.value_end-1,s.value_end-1,'\t'+h+'\n')]);s=parse(t)[0]
   for key,val in [('manpower',str(alloc[sid]['population'])),('resources','{ '+ ' '.join(f'{k} = {v}' for k,v in alloc[sid]['resources'].items())+' }')]:t=set_field(t,s,key,val);s=parse(t)[0]
   if not s.get('state_category'):t=set_field(t,s,'state_category',old[primary][2].val('state_category'));s=parse(t)[0]
   state_report.append({'state':sid,'primary_source':primary,'sources':dict(sources),'politics':politics[str(sid)],'cleared_inactive_cores_claims':removed,'infrastructure':int(infra),'population':alloc[sid]['population'],'resources':alloc[sid]['resources']})
  if sid in NAMES:
   dest=p.with_name(str(sid)+'-'+NAMES[sid][1]+'.txt');assert dest==p or not dest.exists(),('filename collision',dest)
  else:dest=p
  if dest!=p:renames.append({'state':sid,'old':p.relative_to(ROOT).as_posix(),'new':dest.relative_to(ROOT).as_posix()})
  if t!=p.read_text('utf-8-sig') or dest!=p:dest.write_text(t,'utf-8')
  if dest!=p:p.unlink()
 dump(OUT/'state-changes.json',state_report);dump(OUT/'renames.json',renames);dump(OUT/'actual-building-transfers.json',{'moves':building_moves,'air_base_state_mapping':airport_moves,'rule':'Occupied model anchors/attached province retain location; infrastructure inherited separately, no new actual industry'})
 dump(BASE/'initial_territories.json',politics);dump(OUT/'political-relations.json',politics)
 # The current VP inventory keeps scores/names/positions and updates hosts only.
 vp=json.loads((BASE/'modern_victory_points.json').read_text('utf-8'));moved=[]
 for pid,item in vp['province_id_inventory'].items():
  target=npmap[int(pid)]
  if item['state_id']!=target:moved.append({'province':int(pid),'from':item['state_id'],'to':target,'score':item['score']});item['state_id']=target
 dump(BASE/'modern_victory_points.json',vp);dump(OUT/'victory-point-transfers.json',moved)
 update_models(oldmodels,npmap,op,raster,defs,affected)
 update_names(renames)
 update_references(airport_moves,npmap,old,affected)
 index={str(sid):p.name for sid,(p,_,_) in statefiles(ROOT/'history/states').items()};dump(BASE/'current_state_files.json',index);dump(OUT/'state-index.json',index)
 print(json.dumps({'written_states':len(state_report),'renames':len(renames),'vp_migrated':len(moved),'strategic_regions':region_changes,'editor_omissions_repaired':len(missing),'building_transfers':len(building_moves)},ensure_ascii=False))

def update_models(oldmodels,npmap,op,raster,defs,affected):
 import numpy as np
 from PIL import Image
 H,W=raster.shape;rows=[];moves=[];slots=collections.Counter();by_state=collections.defaultdict(list);by_prov=collections.defaultdict(list)
 for row,pid,actual in oldmodels:
  oldsid=int(row[0]);row=list(row)
  # Keep genuine coordinates/rotation; new ownership follows the actual land.
  if actual and actual!=oldsid and (oldsid in affected or actual in affected):row[0]=str(actual);moves.append({'kind':row[1],'province':pid,'from':oldsid,'to':actual})
  rows.append(row);slots[int(row[0]),row[1]]+=1
  if actual==int(row[0]) and row[1]!='floating_harbor':by_state[actual].append(row);by_prov[pid].append(row)
 files={p.name:p for p in (GAME/'common/buildings').glob('*.txt')};files.update({p.name:p for p in (ROOT/'common/buildings').glob('*.txt')});buildings={};spawns={}
 for p in files.values():
  for n in parse(p.read_text('utf-8-sig')):
   if n.key=='buildings':buildings.update({v.key:v for v in n.children})
   if n.key=='spawn_points':spawns.update({v.key:v for v in n.children})
 required={};prov_required={}
 for kind,n in buildings.items():
  show=n.val('show_on_map');spawn=n.val('spawn_point')
  if not show:continue
  if spawn:
   sn=spawns[spawn]
   if sn.val('disable_auto_nudging')=='yes':continue
   target=required if sn.val('type')=='state' else prov_required
   target[spawn]=(max(int(sn.val('max','1')),target.get(spawn,(0,False))[0]),sn.val('only_costal')=='yes')
  else:
   cap=n.get('level_cap');isprov=bool(cap and cap.get('province_max'));target=prov_required if isprov else required
   target[kind]=(max(int(show),target.get(kind,(0,False))[0]),n.val('only_costal')=='yes')
 added=[];height=np.asarray(Image.open(ROOT/'map/heightmap.bmp'));state_pids=collections.defaultdict(list)
 for pid,sid in npmap.items():state_pids[sid].append(pid)
 def anchor(sid,pid=None,coastal=False):
  candidates=by_prov.get(pid,[]) if pid is not None else by_state.get(sid,[])
  if coastal:
   candidates=[r for r in candidates if defs[int(raster[H-1-math.floor(float(r[4])),math.floor(float(r[2]))])]['coastal']=='true']
   candidates=sorted(candidates,key=lambda r:r[1] not in ['naval_base_spawn','dockyard'])
   assert candidates,('Missing existing coastal anchor',sid)
  if candidates:return list(candidates[0])
  mask=(raster==pid) if pid is not None else np.isin(raster,state_pids[sid]);yy,xx=np.nonzero(mask);assert len(xx),('empty model anchor',sid,pid)
  i=int(np.argmin((xx-xx.mean())**2+(yy-yy.mean())**2));x=int(xx[i]);y=int(yy[i]);return [str(sid),'anchor',f'{x:.2f}',f'{max(10,float(height[y,x])/10):.2f}',f'{H-1-y:.2f}','0.00','0']
 def add(sid,kind,ref,pid=None):
  row=list(ref);row[0]=str(sid);row[1]=kind
  if kind not in ['naval_base_spawn','floating_harbor']:row[6]='0'
  rows.append(row);slots[sid,kind]+=1;added.append({'state':sid,'kind':kind,'province':pid,'coordinates':row[2:5]})
 for sid in sorted(affected):
  coast=any(defs[p]['coastal']=='true' for p in state_pids[sid])
  for kind,(count,coastal) in required.items():
   if coastal and not coast:continue
   while slots[sid,kind]<count:add(sid,kind,anchor(sid,coastal=coastal))
 # Spawn points belong to individual provinces, not a single arbitrary state point.
 pcounts=collections.Counter()
 for row in rows:
  if row[1]=='floating_harbor':continue
  x,z=math.floor(float(row[2])),math.floor(float(row[4]));pcounts[int(raster[H-1-z,x]),row[1]]+=1
 for sid in sorted(affected):
  for pid in state_pids[sid]:
   for kind,(count,coastal) in prov_required.items():
    if coastal and defs[pid]['coastal']!='true':continue
    while pcounts[pid,kind]<count:add(sid,kind,anchor(sid,pid),pid);pcounts[pid,kind]+=1
 (ROOT/'map/buildings.txt').write_text('\n'.join(';'.join(r) for r in rows),'utf-8')
 dump(OUT/'model-changes.json',{'moved':moves,'added':added,'required_state_models':required,'required_province_models':prov_required,'records':len(rows),'no_actual_buildings_created':True})

def update_names(renames):
 # Geographic aliases only; victory-point names remain names of the same cities.
 alias=re.compile(r'^(?:STATE_(\d+)|[A-Za-z0-9]+_STATE_(\d+)|STATE_(\d+)_[A-Za-z0-9_]+|state_(\d+)_name|(\d+)_[A-Za-z0-9_]+_name)$')
 changes=[]
 for lang in LANGS:
  value_index={'simp_chinese':0,'russian':2,'japanese':3,'korean':4}.get(lang,1)
  for p in (ROOT/'localisation').rglob('*.yml'):
   if not p.name.endswith('_l_'+lang+'.yml'):continue
   t=p.read_text('utf-8-sig');lines=t.splitlines(keepends=True);touched=False;existing=set()
   for i,line in enumerate(lines):
    m=re.match(r'^(\s*)([A-Za-z0-9_.-]+):(-?\d+)\s+"((?:\\.|[^"\\])*)"(.*?)(\r?\n)?$',line)
    if not m:continue
    key=m[2];existing.add(key);am=alias.fullmatch(key)
    if not am:continue
    sid=int(next(v for v in am.groups() if v))
    if sid not in NAMES:continue
    value=NAMES[sid][value_index]
    if m[4]!=value or m[3]!='0':lines[i]=m[1]+key+':0 "'+value+'"'+m[5]+'\n';changes.append({'file':p.relative_to(ROOT).as_posix(),'key':key,'before':m[4],'after':value});touched=True
   if p.name=='zzzz_apdc_map_geography_l_'+lang+'.yml':
    for sid,names in sorted(NAMES.items()):
     key='STATE_'+str(sid)
     if key not in existing:lines.append(' '+key+':0 "'+names[value_index]+'"\n');changes.append({'file':p.relative_to(ROOT).as_posix(),'key':key,'before':None,'after':names[value_index]});touched=True
   if touched:p.write_text(''.join(lines),'utf-8-sig',newline='\n')
 dump(OUT/'localisation-changes.json',changes)
 dump(OUT/'name-decisions.json',{'names':{str(k):dict(zip(['simp_chinese','english','russian','japanese','korean'],v)) for k,v in NAMES.items()},'latin_languages':'Use current official/transliterated English spellings where no distinct established form is maintained.','sources':{'Thar Desert':'https://www.tourism.rajasthan.gov.in/bikaner.html','Parbhani':'https://parbhani.gov.in/en/','Ichalkaranji':'https://www.gazetteers.maharashtra.gov.in/cultural.maharashtra.gov.in/english/gazetteer/KOLHAPUR/places_Ichalkaranji.html','Rajapalayam':'https://www.tnurbantree.tn.gov.in/rajapalayam/'},'chinese_names':'User supplied; preserved verbatim. 1562 expanded after user clarification.'})

def update_references(airport_moves,npmap,old,affected):
 # Released-country capital city anchors, not automatic relocation to new centres.
 anchors={'HYD':8087,'RAJ':2086,'KOL':1349,'RAS':10278,'MYS':4315,'CIP':18987,'RJP':1908,'WIS':9975}
 changed=[]
 for p in (ROOT/'history/countries').glob('*.txt'):
  tag=p.name[:3];t=p.read_text('utf-8-sig');nodes=parse(t);edits=[]
  for n in nodes:
   if n.key=='capital' and tag in anchors and int(n.value) in affected:
    target=npmap[anchors[tag]]
    if target!=int(n.value):edits.append((n.value_start,n.value_end,str(target)));changed.append({'file':p.relative_to(ROOT).as_posix(),'kind':'capital','province':anchors[tag],'from':int(n.value),'to':target,'reason':'Keep original named capital city; no new owner/country settings'})
  if edits:p.write_text(patches(t,edits),'utf-8')
 # Air deployment dictionaries are keyed by the air-base STATE, not province.
 for p in (ROOT/'history/units').glob('*.txt'):
  t=p.read_text('utf-8-sig');edits=[]
  for n in walk(parse(t)):
   if n.key=='air_wings':
    for child in n.children:
     if child.key.isdigit() and int(child.key) in airport_moves and int(child.key)!=airport_moves[int(child.key)]:
      a=int(child.key);b=airport_moves[a];edits.append((child.start,child.start+len(child.key),str(b)));changed.append({'file':p.relative_to(ROOT).as_posix(),'kind':'air_wings_base','from':a,'to':b})
  if edits:p.write_text(patches(t,edits),'utf-8')
 dump(OUT/'geographic-reference-changes.json',changed)

def audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pstate=pmap(states);defs,raster=raster_data();H,W=raster.shape;issues=[]
 assert len(states)==1578 and set(range(1,1579))==set(states)
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

QA=Path('C:/Users/ASUS/.codex/tmp/APDC_MapMaintenanceQA')

def prepare_qa():
 assert (OUT/'static-audit.json').exists() and (OUT/'cold-war-refresh.json').exists()
 assert not QA.exists(), 'Existing profile must be inspected before reuse'
 (QA/'mod').mkdir(parents=True);driver=QA/'driver'
 for rel in ['common/on_actions','common/defines']:(driver/rel).mkdir(parents=True)
 desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M)
 (QA/'mod/APDC.mod').write_text(desc,'utf-8')
 (QA/'mod/APDC_MapMaintenanceQA.mod').write_text('name="APDC isolated map maintenance diagnostics"\npath="'+driver.as_posix()+'"\nsupported_version="1.19.*"\n','utf-8')
 dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_MapMaintenanceQA.mod'],'disabled_dlcs':[]})
 settings=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/settings.txt').read_text('utf-8-sig')
 settings=settings.replace('save_career_to_cloud=yes','save_career_to_cloud=no').replace('telemetry_enabled=yes','telemetry_enabled=no')
 (QA/'settings.txt').write_text(settings,'utf-8')
 (driver/'common/defines/zzzz_APDC_map_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf-8')
 daily='add_to_variable = { apdc_qa_map_day = 1 }\n'
 checks=''
 authority=json.loads((BASE/'initial_territories.json').read_text('utf-8'))
 for sid in range(1559,1579):
  p=authority[str(sid)];conditions=f'is_owned_by = {p["owner"]} is_controlled_by = {p["controller"]} '+' '.join('is_core_of = '+tag for tag in p['cores'])
  checks+=f'{sid} = {{ if = {{ limit = {{ {conditions} }} log = "APDC_MAP_20261102 PASS state_{sid}" }} else = {{ log = "APDC_MAP_20261102 FAIL state_{sid}" }} }}\n'
 daily+='if = { limit = { check_variable = { apdc_qa_map_day = 1 } } apdc_cw_open_panel = yes '+checks+'log = "APDC_MAP_20261102 WORLD_READY pieces=[?apdc_cw_world_piece_rows^num] borders=[?apdc_cw_world_border_visible^num]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_map_day = 10 } } set_variable = { apdc_cw_selected = PAK } set_variable = { apdc_cw_detail = 1 } apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261102 PAK_DETAIL_READY states=[?apdc_cw_detail_state_count] pieces=[?apdc_cw_detail_pieces^num]" }\n'
 daily+='if = { limit = { check_variable = { apdc_qa_map_day = 25 } } set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes log = "APDC_MAP_20261102 WORLD_RETURNED" }\n'
 daily+='log = "APDC_MAP_20261102 DAY [?apdc_qa_map_day] date=[GetDateText]"\n'
 (driver/'common/on_actions/zzzz_APDC_map_qa.txt').write_text('on_actions = { on_startup = { effect = { log = "APDC_MAP_20261102 START" } } on_daily_GER = { effect = {\n'+daily+'} } }\n','utf-8')
 protected=[]
 for name in ['dlc_load.json','settings.txt','continue_game.json','last_save']:
  p=USER/name
  if p.is_file():protected.append(p)
 protected.extend(p for p in (USER/'save games').glob('*') if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower()))
 dump(OUT/'runtime-preparation.json',{'profile':str(QA),'driver':str(driver),'user_files_before':{str(p):sha(p) for p in protected},'user_enabled_mods':json.loads((USER/'dlc_load.json').read_text('utf-8-sig')),'test_mods':['APDC','isolated diagnostics'],'disabled_dlcs':[],'toolpack_loaded':False,'scene':'GER 2060 ordinary start; no user desktop input; world, PAK core detail, return','direct_source_project':str(ROOT),'external_launcher_descriptor':(USER/'mod/APDC.mod').read_text('utf-8-sig')})
 print(str(QA))

def section(text,name):
 m=re.search(r'(?m)^'+re.escape(name)+r'=\{',text);assert m,('save section missing',name);start=m.end();depth=1
 for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
  if token.group()=='{':depth+=1
  elif token.group()=='}':
   depth-=1
   if depth==0:return text[start:start+token.start()]
 raise ValueError('incomplete save '+name)

def runtime_audit():
 save=QA/'save games/autosave.hoi4';text=save.read_text('utf-8-sig');native={int(n.key):n for n in parse(section(text,'states'))};authority=json.loads((BASE/'initial_territories.json').read_text('utf-8'));assert len(native)==len(authority)
 cores=collections.defaultdict(list);claims=collections.defaultdict(list);country_count=0
 for match in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',section(text,'countries')):
  tag,body=match.groups();country_count+=1
  for key,target in [('cores',cores),('claims',claims)]:
   m=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
   if m:
    for sid in map(int,re.findall(r'\d+',m[1])):target[sid].append(tag)
 assert country_count>100
 differences=[];dmz=[]
 for sid,n in native.items():
  got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])};want=authority[str(sid)];want={**want,'cores':sorted(want['cores']),'claims':sorted(want['claims'])}
  if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
  if n.val('demilitarized')=='yes':dmz.append(sid)
 game=(QA/'logs/game.log').read_text('utf-8-sig',errors='replace');error=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');evidence=[line for line in game.splitlines() if 'APDC_MAP_20261102' in line]
 relevant=[line for line in error.splitlines() if re.search(r'MAP_ERROR|Province with id:|State \d+ has no|(?:railway|Railway)|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect',line)]
 prep=json.loads((OUT/'runtime-preparation.json').read_text('utf-8'));user_changes=[p for p,h in prep['user_files_before'].items() if sha(Path(p))!=h]
 stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));date=re.search(r'(?m)^date="([^"]+)"',text)[1]
 passed=not(differences or dmz or relevant or user_changes) and 'FAIL' not in '\n'.join(evidence) and all(any(key in line for line in evidence) for key in ['WORLD_READY','PAK_DETAIL_READY','WORLD_RETURNED']) and not(stop['still_running'] or stop['steam_app_running'] or stop['remaining_helpers']) and date.startswith('2060.')
 report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'states':len(native),'countries_read':country_count,'relation_differences':differences,'initial_dmz':dmz,'relevant_map_cold_war_errors':relevant,'all_error_log_lines':len(error.splitlines()),'evidence':evidence,'process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),'stop':stop,'user_file_changes':user_changes,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf-8')),'input_desktop_switched':False,'mouse_keyboard_sent':False}
 dump(OUT/'runtime-audit.json',report)
 with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
  for p in (QA/'logs').glob('*'):
   if p.is_file():z.write(p,'logs/'+p.name)
  for name in ['silent-process.json','silent-stop.json','dlc_load.json','settings.txt']:
   if (QA/name).is_file():z.write(QA/name,name)
 assert passed,report
 print(json.dumps({k:v for k,v in report.items() if k not in ['evidence','process','enabled_mods']},ensure_ascii=False))

def review():
 import numpy as np
 from PIL import Image,ImageFilter
 states=statefiles(ROOT/'history/states');pstate=pmap(states);definitions,raster=raster_data();g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf-8'));prefix='gfx/interface/APDC/cold_war/'
 assert set(map(int,g['states']))==set(states)
 checked=[]
 for e in g['pieces']:
  field=np.asarray(Image.open(ROOT/prefix/'map'/(e['name']+'.png')))
  mask=np.pad(np.isin(raster[e['y']:e['y']+e['h'],e['x']:e['x']+e['w']], [int(x.key) for x in states[e['state']][2].get('provinces').children]),e['padding'])
  assert np.array_equal(field[:,:,0]>127,mask),('state texture does not match current province raster',e['name']);checked.append(e['name'])
 with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
  old=json.loads(z.read('docs/cold-war/20261024/geometry.json'));oldpol=json.loads(z.read('tools/map_maintenance/baseline/initial_territories.json'));newpol=json.loads((BASE/'initial_territories.json').read_text('utf-8'))
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
  before=world(old,oldpol,True);after=world(g,newpol);before.save(OUT/'world-before.png');after.save(OUT/'world-after.png')
  changed=np.any(np.asarray(before)!=np.asarray(after),axis=2)
  affected=set(json.loads((OUT/'plan.json').read_text('utf-8'))['affected_states']);pids=[pid for pid,sid in pstate.items() if sid in affected]
  allowed=Image.fromarray(np.isin(raster,pids).astype('uint8')*255).resize((1000,500),Image.Resampling.LANCZOS).filter(ImageFilter.MaxFilter(9))
  outside=int(np.count_nonzero(changed & (np.asarray(allowed)==0)));assert outside==0,('unrelated world pixels changed',outside)
  protected=['palette.png','background.png','screen_overlay.png','pie_frame.png','option.png','control.png']
  protected=[v for v in protected if (ROOT/prefix/v).exists() and prefix+v in z.namelist()]
  assert all(z.read(prefix+v)==(ROOT/prefix/v).read_bytes() for v in protected)
 sys.path.insert(0,str(ROOT/'tools/cold_war'));import render_review
 detail,info=render_review.map_detail(g,'PAK');detail.save(OUT/'PAK-core-detail-source.png')
 native=[]
 if (OUT/'runtime-visual-captures.json').exists():
  native=json.loads((OUT/'runtime-visual-captures.json').read_text('utf-8'))
  # Same world before and after entering details, with identical country data.
  a=np.asarray(Image.open(OUT/'runtime-world.png'))[150:650,458:1458]
  b=np.asarray(Image.open(OUT/'runtime-world-return.png'))[150:650,458:1458]
  world_return_diff=int(np.count_nonzero(np.any(a!=b,axis=2)))
 else:world_return_diff=None
 dump(OUT/'visual-asset-audit.json',{'state_masks_exact':len(checked),'world_changed_pixels':int(changed.sum()),'unrelated_world_changed_pixels':outside,'palette_scales_and_non_map_art_preserved':True,'protected_art':protected,'native_capture_count':len(native),'native_world_first_vs_return_diff_pixels':world_return_diff,'PAK_detail_source_review':info,'native_visual_review':'See three native private-desktop captures; evaluated separately from deterministic source review.'})
 city_review()
 print(json.dumps({'state_masks_exact':len(checked),'world_diff':int(changed.sum()),'outside_affected_states_diff':outside,'native_world_return_diff':world_return_diff,'PAK':info},ensure_ascii=False))

def city_review():
 import unicodedata
 def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower())
 source_dir=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/GF-MAP/.codex_backups/20261020-183551-chinese-city-name-corrections');source=source_dir/'现代胜利点总表.json'
 data=json.loads(source.read_text('utf-8-sig'));states=statefiles(ROOT/'history/states');pstate=pmap(states)
 assert sha(ROOT/'map/provinces.bmp')==sha(BASE/'imported_provinces.bmp'), 'Changed province shapes require rechecking individual city coordinates'
 regional={1559,1562,1563,1571,1573,1577,1578,1144,1145,986,439};aliases={1560:['Delhi'],427:['Chanda'],1572:['Shimoga'],1574:['Tellicherry']};rows=[];mismatch=[];unresolved=[]
 for sid,names in sorted(NAMES.items()):
  if sid in regional:rows.append({'state':sid,'name':names[0],'kind':'region/islands/desert, not a city-named state'});continue
  wanted={norm(v) for v in [names[1]]+aliases.get(sid,[])};matches=[]
  for row in data:
   labels=[row.get(k,'') for k in ['name','ascii','ucdb_name']]+[row.get('names',{}).get('english','')]
   own=bool(wanted & {norm(v) for v in labels})
   members=[v for v in row.get('same_province_cities',[]) if norm(v['name']) in wanted]
   if own or members:matches.append({'city':members[0]['name'] if members else row['name'],'province':row['province_id'],'actual_state':pstate[row['province_id']],'representative_city':row['name'],'ucdb_id':members[0]['ucdb_id'] if members else row['ucdb_id'],'same_province_member':bool(members),'provenance':'Recorded same-province city membership, not borrowing the representative city coordinates' if members else 'Verified city province in fixed modern gazetteer'})
  inside=[v for v in matches if v['actual_state']==sid]
  entry={'state':sid,'name':names[0],'english':names[1],'matches':matches,'inside_named_state':bool(inside)};rows.append(entry)
  if not matches:unresolved.append(entry)
  elif not inside:mismatch.append(entry)
 dump(OUT/'city-named-state-review.json',{'source':str(source),'source_sha256':sha(source),'province_raster_matches_fixed_import':True,'method':'Existing verified city province / same-province city groups, remapped through CURRENT state lists; no new VP, score or border change.','rows':rows,'mismatches':mismatch,'unresolved':unresolved})
 current=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf-8'));current['latest_added_renamed_state_review']={'date':'2026-11-02','report':'docs/map-maintenance/20261102/city-named-state-review.json','city_named_states_checked':len(NAMES)-len(regional),'mismatches':mismatch,'unresolved':unresolved};dump(BASE/'city_named_state_mismatches.json',current)
 print('City name review',len(NAMES)-len(regional),'mismatches',len(mismatch),'unresolved',len(unresolved))

def checkpoint():
 from concurrent.futures import ThreadPoolExecutor
 states=statefiles(ROOT/'history/states');index={str(sid):p.name for sid,(p,_,_) in states.items()};assert index==json.loads((BASE/'current_state_files.json').read_text('utf-8'))
 runtime=json.loads((OUT/'runtime-audit.json').read_text('utf-8'));static=json.loads((OUT/'static-audit.json').read_text('utf-8'));visual=json.loads((OUT/'visual-asset-audit.json').read_text('utf-8'));assert runtime['passed'] and static['passed'] and visual['native_capture_count']==3 and visual['native_world_first_vs_return_diff_pixels']==0
 state_archive=OUT/'states-checkpoint.zip'
 with zipfile.ZipFile(state_archive,'w',zipfile.ZIP_DEFLATED) as z:
  for sid,(p,_,_) in sorted(states.items()):z.write(p,p.name)
 dump(OUT/'state-hashes.json',{str(sid):{'file':p.name,'sha256':sha(p)} for sid,(p,_,_) in states.items()})
 map_archive=OUT/'map-checkpoint.zip'
 with zipfile.ZipFile(map_archive,'w',zipfile.ZIP_DEFLATED) as z:
  for rel in ['map/buildings.txt','map/railways.txt','map/supply_nodes.txt','map/adjacencies.csv','docs/cold-war/20261024/geometry.json','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json']:
   z.write(ROOT/rel,rel)
  for p in (ROOT/'map/strategicregions').glob('*.txt'):z.write(p,p.relative_to(ROOT).as_posix())
 dump(BASE/'latest_checkpoint.json',{'date':'2026-11-02','report':OUT.relative_to(ROOT).as_posix(),'state_history_archive':state_archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(state_archive),'political_relations':'tools/map_maintenance/baseline/initial_territories.json','state_index':'tools/map_maintenance/baseline/current_state_files.json','cold_war_geometry':'docs/cold-war/20261024/geometry.json','cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'GER 2060.2.1.1 save; all 1578 state relations match; native world/PAK core detail/return captures reviewed; owned games/helpers closed','runtime_report':(OUT/'runtime-audit.json').relative_to(ROOT).as_posix(),'visual_report':(OUT/'visual-asset-audit.json').relative_to(ROOT).as_posix(),'backup':str(BACKUP),'previous_report':'docs/map-maintenance/20261028-black-zone-910','geography_backup':str(BACKUP),'railways':'map/railways.txt','railways_sha256':sha(ROOT/'map/railways.txt'),'railways_checkpoint':'docs/map-maintenance/20261027-railways/railways-checkpoint.txt','map_checkpoint_archive':map_archive.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(map_archive),'states':len(states),'post_runtime_coordinate_only_adjustments':'Two zero-level dockyard spawn coordinates moved to existing coastal anchors; static rechecked, no further game launch'})
 before=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'));cw=json.loads((OUT/'cold-war-refresh.json').read_text('utf-8'));renames=json.loads((OUT/'renames.json').read_text('utf-8'));loc=json.loads((OUT/'localisation-changes.json').read_text('utf-8'))
 allowed={v['file'] for v in cw['changed']}|{v['file'] for v in loc}|{v['new'] for v in renames}
 allowed|={'tools/map_maintenance/finish_20261102.py','tools/cold_war/refresh_geography.py','map/buildings.txt','common/scripted_triggers/GER_scripted_triggers.txt','tools/map_maintenance/baseline/initial_territories.json','tools/map_maintenance/baseline/current_state_files.json','tools/map_maintenance/baseline/latest_checkpoint.json','tools/map_maintenance/baseline/modern_victory_points.json','tools/map_maintenance/baseline/city_named_state_mismatches.json'}
 allowed|={r['file'] for r in json.loads((OUT/'geographic-reference-changes.json').read_text('utf-8'))}
 allowed|={p.relative_to(ROOT).as_posix() for sid,(p,_,_) in states.items() if sid in set(json.loads((OUT/'plan.json').read_text('utf-8'))['affected_states'])}
 allowed|={'map/strategicregions/'+p.name for p in (ROOT/'map/strategicregions').glob('*.txt') if int(parse(p.read_text('utf-8-sig'))[0].val('id')) in json.loads((OUT/'strategic-repairs.json').read_text('utf-8'))['written_regions']}
 allowed|={'项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md'}
 files=[]
 for folder,dirs,names in os.walk(ROOT):
  dirs[:]=[d for d in dirs if d not in ['.git','__pycache__']]
  files.extend(Path(folder)/name for name in names if Path(folder)/name!=OUT/'preservation-audit.json')
 def inspect(p):
  rel=p.relative_to(ROOT).as_posix();v=sha(p);return rel,v,before.get(rel,{}).get('sha256')
 with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(inspect,files))
 changed=[{'file':rel,'before':old,'after':new} for rel,new,old in rows if old and old!=new];added=[{'file':rel,'sha256':new} for rel,new,old in rows if not old];removed=[rel for rel in before if not (ROOT/rel).exists()]
 allowed_removed={x['old'] for x in renames};unexpected=[x for x in changed+added if x['file'] not in allowed and not x['file'].startswith(OUT.relative_to(ROOT).as_posix()+'/')];unexpected_removed=sorted(set(removed)-allowed_removed)
 protected=['gfx/FX/border.shader','gfx/FX/pdxmap.shader','gfx/FX/pdxwater.shader','gfx/FX/gf_map_style.fxh','gfx/FX/APDC_cw_palette.shader','gfx/interface/APDC/cold_war/palette.png','gfx/interface/APDC/cold_war/background.png','map/provinces.bmp','map/definition.csv','map/heightmap.bmp','map/rivers.bmp','map/railways.txt','map/supply_nodes.txt','AGENTS.md']
 preserved={rel:sha(ROOT/rel)==before[rel]['sha256'] for rel in protected if rel in before};assert all(preserved.values()),preserved
 report={'passed':not unexpected and not unexpected_removed,'before_files':len(before),'current_hashed_files':len(rows),'changed_existing':changed,'added':added,'removed_by_authorized_rename':removed,'unexpected_changes':unexpected,'unexpected_removed':unexpected_removed,'protected_file_hashes_preserved':preserved,'fixed_original_economy_and_import_snapshots_preserved':not any(x['file'].startswith(('tools/map_maintenance/baseline/original_economy','tools/map_maintenance/baseline/imported_')) for x in changed),'preexisting_dirty_content_preserved_outside_scope':True,'source_user_name_decisions':{'10816':436,'18987':437,'1562':'拉夫沙漠'},'game_sessions':['initial ordinary run, passed','targeted visual retry after first run ended before capture, passed'],'user_desktop_input':False}
 dump(OUT/'preservation-audit.json',report);assert report['passed'],report
 dump(BACKUP/'final-file-manifest.json',{rel:{'sha256':new} for rel,new,_ in rows})
 dump(BACKUP/'task.json',{'date':'2026-11-02','request':'Finish user-edited India state/province assignments and synchronize Cold War map, following root AGENTS','new_states':{str(k):v[0] for k,v in NAMES.items() if k>=1559},'renamed_states':{str(k):v[0] for k,v in NAMES.items() if k<1559},'user_replies':{'10816':'436 Bhopal','18987':'437 Ujjain','1562':'拉夫沙漠'},'note':'No party/leader/economy/art redesign authorized'})
 print(json.dumps({'passed':report['passed'],'checked_files':len(rows),'changed':len(changed),'added':len(added),'renamed_old_paths':len(removed),'unexpected':unexpected,'unexpected_removed':unexpected_removed,'state_archive':str(state_archive)},ensure_ascii=False))

if __name__=='__main__':globals()[sys.argv[1]]()
