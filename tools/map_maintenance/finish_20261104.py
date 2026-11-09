"""2026-11-04 Siberia/Mongolia/Iraq map maintenance.
Reviewed date-specific migration. Plan first; apply only against its byte backup.
Fixed economy inputs are immutable; country identity and non-geographic gameplay stay APDC.
"""
from pathlib import Path
import sys,json,hashlib,zipfile,collections,csv,re,io,math,os,shutil
from fractions import Fraction
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'D:/APDC_ColdWarTools/pydeps313')
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,walk,patches
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-map-finish-20261104.json').read_text('utf-8'))
BACKUP=Path(META['backup']);OUT=ROOT/META['report'];BASE=ROOT/'tools/map_maintenance/baseline'
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
USER=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
LANGS=['simp_chinese','english','french','german','spanish','braz_por','polish','russian','japanese','korean']
NAMES={int(k):v for k,v in {
 "1579": [
  "外阿穆尔",
  "Outer Amur",
  "Внешнее Приамурье",
  "外アムール",
  "외아무르"
 ],
 "1580": [
  "别洛戈尔斯克",
  "Belogorsk",
  "Белогорск",
  "ベロゴルスク",
  "벨로고르스크"
 ],
 "1581": [
  "布列亚山区",
  "Bureya Mountains",
  "Буреинские горы",
  "ブレヤ山地",
  "부레야 산지"
 ],
 "1582": [
  "迈斯基山脊",
  "Maysky Range",
  "Майский хребет",
  "マイスキー山脈",
  "마이스키 산맥"
 ],
 "1583": [
  "阿纳德尔",
  "Anadyr",
  "Анадырь",
  "アナディリ",
  "아나디리"
 ],
 "1584": [
  "阿扬",
  "Ayan",
  "Аян",
  "アヤン",
  "아얀"
 ],
 "1585": [
  "科雷马山脉",
  "Kolyma Mountains",
  "Колымское нагорье",
  "コリマ山地",
  "콜리마 산지"
 ],
 "1586": [
  "帕拉纳",
  "Palana",
  "Палана",
  "パラナ",
  "팔라나"
 ],
 "1587": [
  "雅库茨克",
  "Yakutsk",
  "Якутск",
  "ヤクーツク",
  "야쿠츠크"
 ],
 "1588": [
  "阿姆加",
  "Amga",
  "Амга",
  "アムガ",
  "암가"
 ],
 "1589": [
  "奥伊米亚康斯克",
  "Oymyakonsky",
  "Оймяконский",
  "オイミャコンスキー",
  "오이먀콘스키"
 ],
 "1590": [
  "乌斯季亚纳",
  "Ust-Yana",
  "Усть-Яна",
  "ウスチ・ヤナ",
  "우스티야나"
 ],
 "1591": [
  "日甘斯克",
  "Zhigansk",
  "Жиганск",
  "ジガンスク",
  "지간스크"
 ],
 "1592": [
  "连斯克",
  "Lensk",
  "Ленск",
  "レンスク",
  "렌스크"
 ],
 "1593": [
  "通卡",
  "Tunka",
  "Тунка",
  "トゥンカ",
  "툰카"
 ],
 "1594": [
  "外贝加尔",
  "Transbaikalia",
  "Забайкалье",
  "ザバイカル",
  "자바이칼"
 ],
 "1595": [
  "伊卡",
  "Ika",
  "Ика",
  "イカ",
  "이카"
 ],
 "1596": [
  "基廉斯克",
  "Kirensk",
  "Киренск",
  "キレンスク",
  "키렌스크"
 ],
 "1597": [
  "泰利",
  "Teeli",
  "Тээли",
  "テーリ",
  "테엘리"
 ],
 "1598": [
  "坎斯克",
  "Kansk",
  "Канск",
  "カンスク",
  "칸스크"
 ],
 "1599": [
  "瓦纳瓦拉",
  "Vanavara",
  "Ванавара",
  "ヴァナヴァラ",
  "바나바라"
 ],
 "1600": [
  "特恰内",
  "Tychany",
  "Тычаны",
  "ティチャニ",
  "티차니"
 ],
 "1601": [
  "图鲁汉斯基",
  "Turukhansky",
  "Туруханский",
  "トゥルハンスキー",
  "투루한스키"
 ],
 "1602": [
  "多尔加诺-涅涅茨基",
  "Dolgano-Nenetsky",
  "Долгано-Ненецкий",
  "ドルガノ・ネネツキー",
  "돌가노네네츠키"
 ],
 "1603": [
  "巴尔瑙尔",
  "Barnaul",
  "Барнаул",
  "バルナウル",
  "바르나울"
 ],
 "1604": [
  "下瓦尔托夫斯克",
  "Nizhnevartovsk",
  "Нижневартовск",
  "ニジネヴァルトフスク",
  "니즈네바르톱스크"
 ],
 "1605": [
  "巴拉巴",
  "Baraba",
  "Бараба",
  "バラバ",
  "바라바"
 ],
 "1606": [
  "西西伯利亚",
  "Western Siberia",
  "Западная Сибирь",
  "西シベリア",
  "서시베리아"
 ],
 "1607": [
  "库尔干",
  "Kurgan",
  "Курган",
  "クルガン",
  "쿠르간"
 ],
 "1608": [
  "克拉斯诺图林斯克",
  "Krasnoturyinsk",
  "Краснотурьинск",
  "クラスノトゥリインスク",
  "크라스노투린스크"
 ],
 "1609": [
  "苏赫巴托尔",
  "Sukhbaatar",
  "Сухэ-Батор",
  "スフバートル",
  "수흐바타르"
 ],
 "1610": [
  "肯特",
  "Khentii",
  "Хэнтий",
  "ヘンティー",
  "헨티"
 ],
 "1611": [
  "色楞格",
  "Selenge",
  "Сэлэнгэ",
  "セレンゲ",
  "셀렝게"
 ],
 "1612": [
  "东戈壁",
  "Dornogovi",
  "Дорноговь",
  "ドルノゴビ",
  "도르노고비"
 ],
 "1613": [
  "前杭爱",
  "Övörkhangai",
  "Уверхангай",
  "ウブルハンガイ",
  "우부르항가이"
 ],
 "1614": [
  "中戈壁",
  "Dundgovi",
  "Дундговь",
  "ドンドゴビ",
  "돈드고비"
 ],
 "1615": [
  "布尔干",
  "Bulgan",
  "Булган",
  "ボルガン",
  "볼강"
 ],
 "1616": [
  "后杭爱",
  "Arkhangai",
  "Архангай",
  "アルハンガイ",
  "아르항가이"
 ],
 "1617": [
  "巴彦洪戈尔",
  "Bayankhongor",
  "Баянхонгор",
  "バヤンホンゴル",
  "바양홍고르"
 ],
 "1618": [
  "戈壁阿尔泰",
  "Govi-Altai",
  "Говь-Алтай",
  "ゴビ・アルタイ",
  "고비알타이"
 ],
 "1619": [
  "巴彦乌列盖",
  "Bayan-Ölgii",
  "Баян-Улгий",
  "バヤン・ウルギー",
  "바양울기"
 ],
 "1620": [
  "乌布苏",
  "Uvs",
  "Увс",
  "オブス",
  "오브스"
 ],
 "1621": [
  "扎布汗",
  "Zavkhan",
  "Завхан",
  "ザブハン",
  "자브항"
 ],
 "1622": [
  "迈桑",
  "Maysan",
  "Майсан",
  "マイサーン",
  "마이산"
 ],
 "1623": [
  "济加尔",
  "Dhi Qar",
  "Ди-Кар",
  "ジーカール",
  "디카르"
 ],
 "1624": [
  "瓦西特",
  "Wasit",
  "Васит",
  "ワーシト",
  "와시트"
 ],
 "1625": [
  "卡迪西亚",
  "Al-Qadisiyyah",
  "Кадисия",
  "カーディーシーヤ",
  "카디시야"
 ],
 "1626": [
  "萨拉赫丁",
  "Saladin",
  "Салах-эд-Дин",
  "サラーフッディーン",
  "살라딘"
 ],
 "1627": [
  "苏莱曼尼亚",
  "Sulaymaniyah",
  "Сулеймания",
  "スレイマニヤ",
  "술라이마니야"
 ],
 "1628": [
  "埃尔比勒",
  "Erbil",
  "Эрбиль",
  "アルビール",
  "아르빌"
 ],
 "822": [
  "西楚科奇",
  "Western Chukotka",
  "Западная Чукотка",
  "西チュクチ",
  "서추코트카"
 ],
 "637": [
  "加彼得罗巴普洛夫斯克",
  "Petropavlovsk-Kamchatsky",
  "Петропавловск-Камчатский",
  "ペトロパブロフスク・カムチャツキー",
  "페트로파블롭스크캄차츠키"
 ],
 "574": [
  "涅留恩格里",
  "Neryungri",
  "Нерюнгри",
  "ネリュングリ",
  "네륜그리"
 ],
 "877": [
  "戈尔内",
  "Gorny",
  "Горный",
  "ゴルヌイ",
  "고르니"
 ],
 "876": [
  "阿纳巴尔",
  "Anabar",
  "Анабар",
  "アナバル",
  "아나바르"
 ],
 "575": [
  "米尔内",
  "Mirny",
  "Мирный",
  "ミールヌイ",
  "미르니"
 ],
 "564": [
  "巴温特",
  "Baunt",
  "Баунт",
  "バウント",
  "바운트"
 ],
 "329": [
  "克孜勒",
  "Kyzyl",
  "Кызыл",
  "クズル",
  "키질"
 ],
 "569": [
  "克麦罗沃-哈卡斯",
  "Kemerovo-Khakassia",
  "Кемерово-Хакасия",
  "ケメロヴォ・ハカス",
  "케메로보하카시야"
 ],
 "878": [
  "图拉",
  "Tura",
  "Тура",
  "トゥラ",
  "투라"
 ],
 "40": [
  "鲁布佐夫斯克",
  "Rubtsovsk",
  "Рубцовск",
  "ルプツォフスク",
  "룹촙스크"
 ],
 "577": [
  "汉特-曼西斯克",
  "Khanty-Mansiysk",
  "Ханты-Мансийск",
  "ハンティ・マンシースク",
  "한티만시스크"
 ],
 "582": [
  "设菲尔德",
  "Sheffield",
  "Шеффилд",
  "シェフィールド",
  "셰필드"
 ],
 "653": [
  "叶卡捷琳堡",
  "Yekaterinburg",
  "Екатеринбург",
  "エカテリンブルク",
  "예카테린부르크"
 ],
 "817": [
  "南戈壁",
  "Ömnögovi",
  "Умнеговь",
  "ウムヌゴビ",
  "움누고비"
 ],
 "1142": [
  "哈塞克",
  "Al-Hasakah",
  "Эль-Хасака",
  "ハサカ",
  "하사카"
 ],
 "676": [
  "尼尼微",
  "Nineveh",
  "Ниневия",
  "ニーナワー",
  "니나와"
 ],
 "1143": [
  "迪亚拉",
  "Diyala",
  "Дияла",
  "ディヤーラー",
  "디얄라"
 ],
 "675": [
  "穆萨纳",
  "Al-Muthanna",
  "Мутанна",
  "ムサンナー",
  "무산나"
 ]
}.items()}
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
 return statefiles(ROOT/'history/states')

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
 affected=sorted({v[k] for v in changes for k in ['from','to']} | {sid for sid,(_,_,s) in states.items() if sid in old and not s.get('history')})
 regions={};editor_changes=[]
 for p in (ROOT/'map/strategicregions').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];regions[int(n.val('id'))]=(p,t,n)
 for p in (USER/'map/strategicregions').rglob('*.txt'):
  if p.stat().st_mtime < __import__('datetime').datetime(2026,11,4).timestamp():continue
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
 report={'checkpoint':json.loads((BACKUP/'initial-scan.json').read_text('utf-8'))['checkpoint'],'backup':str(BACKUP),'new_states':sorted(set(states)-set(old)),'affected_states':affected,'province_transfers':changes,'duplicate_resolution':{},'cleared_unchanged_history_restored':[sid for sid in affected if sid in old and set(int(v.key) for v in states[sid][2].get('provinces').children)==set(int(v.key) for v in old[sid][2].get('provinces').children)],'economy_totals':totals,'strategic_editor_changes':editor_changes,'strategic_duplicates':duplicates,'cross_region_states':cross,'model_state_mismatches':wrong,'actual_building_migration_candidates':migrations,'state_sources':{str(sid):dict(collections.Counter(op[int(x.key)] for x in states[sid][2].get('provinces').children)) for sid in affected}}
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
 assert (BACKUP/'manifest-before.json').exists() and not (OUT/'state-changes.json').exists(), 'Apply is a one-time operation against this reviewed backup'
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
 candidates=collections.defaultdict(list)
 for rid,pids in region_lists.items():
  for pid in pids:candidates[pid].append(rid)
 duplicate_repairs=[]
 editor_times={r['region']:Path(r['source']).stat().st_mtime for r in plan['strategic_editor_changes']}
 for pid,rids in candidates.items():
  if len(rids)==1:preg[pid]=rids[0];continue
  # Explicit additions supersede a stale retained entry in the previous
  # region; ties use the latest editor output, then the lowest region ID.
  added=[rid for rid in rids if rid!=preg_old.get(pid) and rid in editor_times]
  winner=min(added or rids,key=lambda rid:(-editor_times.get(rid,0),rid))
  for rid in rids:
   if rid!=winner:region_lists[rid].remove(pid)
  preg[pid]=winner;duplicate_repairs.append({'province':pid,'regions':rids,'selected':winner})
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
 dump(OUT/'strategic-repairs.json',{'missing_editor_provinces_restored':missing,'duplicate_editor_entries_resolved':duplicate_repairs,'cross_state_repairs':repairs,'written_regions':region_changes,'weather_preserved':True})
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
   if not candidates:
    coastal_pids=[p for p in state_pids[sid] if defs[p]['coastal']=='true']
    assert coastal_pids,('No coastal province for required model',sid)
    mask=np.isin(raster,coastal_pids);yy,xx=np.nonzero(mask);i=int(np.argmin((xx-xx.mean())**2+(yy-yy.mean())**2));x=int(xx[i]);y=int(yy[i])
    return [str(sid),'anchor',f'{x:.2f}',f'{max(10,float(height[y,x])/10):.2f}',f'{H-1-y:.2f}','0.00','0']
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
   if defs[pid]['type']!='land':continue
   for kind,(count,coastal) in prov_required.items():
    if coastal and defs[pid]['coastal']!='true':continue
    while pcounts[pid,kind]<count:add(sid,kind,anchor(sid,pid),pid);pcounts[pid,kind]+=1
 (ROOT/'map/buildings.txt').write_text('\n'.join(';'.join(r) for r in rows),'utf-8')
 dump(OUT/'model-changes.json',{'moved':moves,'added':added,'required_state_models':required,'required_province_models':prov_required,'records':len(rows),'no_actual_buildings_created':True})

def update_names(renames):
 # Geographic aliases only; victory-point names remain names of the same cities.
 alias=re.compile(r'^(?:STATE_(\d+)|[A-Za-z0-9_]+_STATE_(\d+)|STATE_(\d+)_[A-Za-z0-9_]+|state_(\d+)_name|(\d+)_[A-Za-z0-9_]+_name)$')
 changes=[]
 for lang in LANGS:
  value_index={'simp_chinese':0,'russian':2,'japanese':3,'korean':4}.get(lang,1)
  for p in (ROOT/'localisation').rglob('*.yml'):
   if not p.name.endswith('_l_'+lang+'.yml'):continue
   t=p.read_text('utf-8-sig');lines=t.splitlines(keepends=True);touched=False;existing=set()
   for i,line in enumerate(lines):
    m=re.match(r'^(\s*)([A-Za-z0-9_.-]+):(-?\d+)\s+"((?:\\.|[^"\\])*)"(.*?)(\r?\n)?$',line)
    if not m:continue
    key=m[2];existing.add(key)
    if key.startswith('APDC_CW_STATE_') or '[' in m[4]:continue
    am=alias.fullmatch(key)
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
 dump(OUT/'name-decisions.json',{'names':{str(k):dict(zip(['simp_chinese','english','russian','japanese','korean'],v)) for k,v in NAMES.items()},'latin_languages':'Use current official/transliterated English spellings where no distinct established form is maintained.','sources':{'Mongolia official atlas':'https://www.mongolianatlas.ac.mn/en/atlas/general','Tychany Russian geographical reference':'https://elib.kspu.ru/upload/documents/books/2012/04/379648aadd4020289c400893761ead80/toponimika-sibiri-i-dalnego-vostoka.pdf','Ika official regional publication':'https://www.ogirk.ru/wp-content/uploads/sm-issue-print/2019/09/ilovepdf_merged-5.pdf'},'chinese_names':'User supplied; preserved verbatim including 637 加彼得罗巴普洛夫斯克 and 582 设菲尔德. These display names do not relocate the states or cities.'})

def update_references(airport_moves,npmap,old,affected):
 # Retain the original capital's actual city even for releasable countries.
 # CKK (Anadyr) and TAY (Dudinka) have no >=50k VP; use their already
 # established city province after verifying current raster/country history.
 anchors={'BYA':14459,'YAK':10641,'CKK':13063}
 changed=[]
 for p in (ROOT/'history/countries').glob('*.txt'):
  tag=p.name[:3];t=p.read_text('utf-8-sig');edits=[]
  for n in parse(t):
   if n.key=='capital' and tag in anchors and int(n.value) in affected:
    pid=anchors[tag]
    if pid not in npmap:continue
    target=npmap[pid]
    if target!=int(n.value):edits.append((n.value_start,n.value_end,str(target)));changed.append({'file':p.relative_to(ROOT).as_posix(),'kind':'capital','province':pid,'from':int(n.value),'to':target,'reason':'Keep original capital city after boundary split'})
  if edits:p.write_text(patches(t,edits),'utf-8')
 for p in (ROOT/'history/units').glob('*.txt'):
  t=p.read_text('utf-8-sig');edits=[]
  for n in walk(parse(t)):
   if n.key=='air_wings':
    for c in n.children:
     if c.key.isdigit() and int(c.key) in airport_moves and int(c.key)!=airport_moves[int(c.key)]:
      a=int(c.key);b=airport_moves[a];edits.append((c.start,c.start+len(c.key),str(b)));changed.append({'file':p.relative_to(ROOT).as_posix(),'kind':'air_wings_base','from':a,'to':b})
  if edits:p.write_text(patches(t,edits),'utf-8')
 dump(OUT/'geographic-reference-changes.json',changed)

def audit():
 import numpy as np
 states=statefiles(ROOT/'history/states');old=previous();pstate=pmap(states);defs,raster=raster_data();H,W=raster.shape;issues=[]
 assert len(states)==1628 and set(range(1,1629))==set(states)
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


if __name__=='__main__':globals()[sys.argv[1]]()
