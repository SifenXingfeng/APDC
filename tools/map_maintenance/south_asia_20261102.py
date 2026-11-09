"""Formalize the 14 countries in the user's NEW MAP save; scoped, date-specific.

Preserves province geometry, population/resources, all art/portraits and
unrelated gameplay. No startup replay. Read plan/report before any apply.
"""
from pathlib import Path
import sys,json,re,hashlib,zipfile,collections,os,shutil,math
sys.dont_write_bytecode=True
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse,walk,patches
META=json.loads(Path('C:/Users/ASUS/.codex/tmp/APDC-south-asia-20261102.json').read_text('utf-8'));BACKUP=Path(META['backup']);OUT=ROOT/META['report'];BASE=ROOT/'tools/map_maintenance/baseline';GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
SCAN=json.loads((BACKUP/'save-scan.json').read_text('utf-8'))
# ID reuse is geographic identity reuse only, not copying 1936 history/leaders.
# RAS is used for the Tamil/Madras identity; Kerala gets its own explicit KER.
COUNTRIES={
 'D10':{'tag':'RAJ','name':'印度共和国','english':'Republic of India','adjective':'印度','rgb':[216,143,70],'basis':'印度三色旗的藏红花色；调整亮度以适配地图','fallback_capital':1560},
 'D11':{'tag':'PAK','name':'巴基斯坦伊斯兰人民共和国','english':'Islamic People\'s Republic of Pakistan','adjective':'巴基斯坦','rgb':[45,113,84],'basis':'巴基斯坦的绿色传统，使用较沉稳的深绿'},
 'D12':{'tag':'KHL','name':'旁遮普解放军','english':'Punjab Liberation Army','adjective':'旁遮普','rgb':[200,189,74],'basis':'旁遮普的Kesari与麦田金色意象，向金黄区分印度橙色'},
 'D13':{'tag':'WIS','name':'古吉拉特共和国','english':'Republic of Gujarat','adjective':'古吉拉特','rgb':[181,173,145],'basis':'古吉拉特纺织与Khadi素布意象的暖灰米色；项目美术取色'},
 'D14':{'tag':'KOL','name':'马拉地共和国','english':'Marathi Republic','adjective':'马拉地','rgb':[198,94,46],'basis':'马拉地Bhagwa藏红花旗传统，使用较深橙色'},
 'D15':{'tag':'MYS','name':'卡纳塔克共和国','english':'Republic of Karnataka','adjective':'卡纳塔克','rgb':[208,182,62],'basis':'卡纳塔克红黄文化配色中的黄色，地图采用金黄'},
 'D16':{'tag':'MLD','name':'马尔代夫共和国','english':'Republic of Maldives','adjective':'马尔代夫','rgb':[50,152,143],'basis':'群岛与海洋身份的青绿，属于地图美术选色而非法定旗色','fallback_capital':281},
 'D17':{'tag':'KER','name':'喀拉拉人民共和国','english':'People\'s Republic of Kerala','adjective':'喀拉拉','rgb':[186,63,84],'basis':'人民共和国的红色意象，兼顾与邻国的明度差异'},
 'D18':{'tag':'SRL','name':'斯里兰卡民主社会主义共和国','english':'Democratic Socialist Republic of Sri Lanka','adjective':'斯里兰卡','rgb':[132,61,81],'basis':'斯里兰卡狮旗的栗红色传统','fallback_capital':422},
 'D19':{'tag':'RAS','name':'泰米尔国','english':'Tamil State','adjective':'泰米尔','rgb':[169,134,70],'basis':'泰米尔历史美术的金铜色意象；不预设具体政治组织'},
 'D20':{'tag':'HYD','name':'安德拉共和国','english':'Republic of Andhra','adjective':'安德拉','rgb':[78,139,116],'basis':'克里希纳河—戈达瓦里河农业地区的绿色意象；项目美术取色'},
 'D21':{'tag':'IPL','name':'印度人民解放军','english':'Indian People\'s Liberation Army','adjective':'印度人民解放军','rgb':[146,46,52],'basis':'人民解放军的革命红色意象，与印度共和国橙色区别'},
 'D22':{'tag':'BAN','name':'孟加拉人民共和国','english':'People\'s Republic of Bengal','adjective':'孟加拉','rgb':[40,116,90],'basis':'孟加拉旗帜与三角洲的绿色传统'},
 'D23':{'tag':'ASM','name':'阿萨姆共和国','english':'Republic of Assam','adjective':'阿萨姆','rgb':[192,116,125],'basis':'阿萨姆Gamosa红白纹饰中的红色，调整为柔和玫红'},
}
RETIRED={'BHU','NEP','BLC','CIP','KAS','KLT','MPU','NWF','RJP','SIN','SKK','PSH','DIP'}
NEW={'KER','IPL','ASM'}
LANGS=['simp_chinese','english','french','german','spanish','braz_por','polish','russian','japanese','korean']
IDEOLOGIES=['communism','socialism','social_democracy','conservatism','liberalism','authoritarianism','dictatorship','fascism','fundamentalism']

def dump(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n','utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(n):return (n.key,n.value,n.op,tuple(canon(x) for x in n.children))
def registry():
 out={}
 for p in sorted((ROOT/'common/country_tags').glob('*.txt')):
  for n in parse(p.read_text('utf-8-sig')):
   if n.value:assert n.key not in out,('duplicate country registration',n.key);out[n.key]=n.value.strip('"')
 return out
def states():
 out={}
 for p in (ROOT/'history/states').glob('*.txt'):
  t=p.read_text('utf-8-sig');n=parse(t)[0];sid=int(n.val('id'));assert sid not in out;out[sid]=(p,t,n)
 return out
def build_plan():
 reg=registry();assert NEW.isdisjoint(reg);assert all(v['tag'] in reg for v in COUNTRIES.values() if v['tag'] not in NEW)
 assert not SCAN['other_dynamic_owners'];assert len(SCAN['states'])==1578
 owned={tag:set(SCAN['countries'][tag]['owned_states']) for tag in COUNTRIES};exclude={'D11','D16','D18','D22','D23'}
 shared=set().union(*(s for tag,s in owned.items() if tag not in exclude))|{1573,733}
 claims_india={787,441,1134,1145,1144,985,434,431}|owned['D23']
 claims_pla={431}|owned['D23'];out={}
 for dynamic,c in COUNTRIES.items():
  d=dict(c);d['dynamic']=dynamic;d['owned']=sorted(owned[dynamic]);d['core']=set(owned[dynamic]);d['claims']=set();d['hex']='#'+''.join(f'{v:02X}' for v in d['rgb']);d['reuses_native_tag']=d['tag'] not in NEW
  if dynamic in ['D10','D21']:d['core']=shared.copy();d['claims']=claims_india.copy() if dynamic=='D10' else claims_pla.copy()
  if dynamic=='D12':d['core']|={439,433,1564,1565};d['claims']=owned['D13'].copy()
  if dynamic=='D14':d['core'].add(427)
  if dynamic=='D16':d['core'].discard(1573)
  if dynamic=='D17':d['core'].add(1573)
  if dynamic=='D20':d['core']-={1577,1578}
  d['core']=sorted(d['core']);d['claims']=sorted(d['claims']);d['capital']=SCAN['countries'][dynamic].get('capital',0)
  if d['capital']==0:d['capital']=d['fallback_capital'];d['capital_reason']='Save value was 0; use valid owned historical capital state'
  else:d['capital_reason']='Preserve valid owned capital from NEW MAP'
  assert d['capital'] in owned[dynamic],('capital not owned',dynamic,d['capital'])
  out[d['tag']]=d
 authority=json.loads((BASE/'initial_territories.json').read_text('utf-8'));mapping={k:v['tag'] for k,v in COUNTRIES.items()};prior={int(sid) for sid,p in authority.items() if p['owner']=='PAK'}
 assert prior==set().union(*owned.values())|{733};assert SCAN['states']['733']['owner']=='BRM'
 for sid in prior:
  src=SCAN['states'][str(sid)];owner=mapping.get(src['owner'],src['owner']);controller=mapping.get(src['controller'],src['controller']);assert not re.fullmatch('D[0-9]{2}',owner);authority[str(sid)]['owner']=owner;authority[str(sid)]['controller']=controller
 target_tags=set(out);obsolete=RETIRED&reg.keys();clean_tags=target_tags|RETIRED
 for sid,p in authority.items():
  p['cores']=[v for v in p['cores'] if v not in clean_tags];p['claims']=[v for v in p['claims'] if v not in clean_tags]
  for tag,d in out.items():
   if int(sid) in d['core']:p['cores'].append(tag)
   if int(sid) in d['claims']:p['claims'].append(tag)
  p['cores']=sorted(set(p['cores']));p['claims']=sorted(set(p['claims']))
 assert not any(p['owner'] in RETIRED or p['controller'] in RETIRED for p in authority.values())
 references=[]
 ignored={'common/scripted_effects/APDC_cold_war_view.txt'}
 def inspect(nodes,parents,p):
  for n in nodes:
   value=n.value.strip('"') if n.value else None
   if n.key in RETIRED or value in RETIRED:references.append({'file':p.relative_to(ROOT).as_posix(),'key':n.key,'value':value,'parents':[x.key for x in parents[-3:]],'op':n.op})
   inspect(n.children,parents+[n],p)
 for folder in ['common','events','history/countries','history/general']:
  for p in (ROOT/folder).rglob('*.txt'):
   rel=p.relative_to(ROOT).as_posix()
   if rel in ignored or (folder=='history/countries' and p.name[:3] in RETIRED):continue
   inspect(parse(p.read_text('utf-8-sig')),[],p)
 OUT.mkdir(parents=True,exist_ok=True);dump(OUT/'country-plan.json',out);dump(OUT/'political-target.json',authority);dump(OUT/'retired-reference-inventory.json',references)
 dump(OUT/'source-analysis.json',{'save':META['source_save'],'sha256':sha(Path(META['source_save'])),'save_date':'2060.1.1.12','dynamic_countries':list(COUNTRIES),'other_dynamic_owners':SCAN['other_dynamic_owners'],'source_unknown_tokens_not_used_for_geography':SCAN['source_unknown_tokens'].splitlines(),'retire_registered':sorted(obsolete),'retired_unregistered_legacy_aliases':sorted(RETIRED-reg.keys()),'source_native_other_change':{'state':733,'owner':'BRM','core_requested':['RAJ','IPL']},'shared_indian_cores':sorted(shared),'core_rules_override_generic_cleanup':True,'no_population_resource_or_province_change':True,'flags_leaders_unchanged':True})
 print(json.dumps({'nations':[{k:d[k] for k in ['dynamic','tag','name','hex','capital']}|{'owned':len(d['owned']),'cores':len(d['core']),'claims':len(d['claims'])} for d in out.values()],'retired_registered':sorted(obsolete),'reference_file_counts':dict(collections.Counter(x['file'] for x in references))},ensure_ascii=False))

def clean_retired_references():
 changes=json.loads((OUT/'retired-reference-cleanup.json').read_text('utf-8')) if (OUT/'retired-reference-cleanup.json').exists() else [];inventory=json.loads((OUT/'retired-reference-inventory.json').read_text('utf-8'));files=sorted({x['file'] for x in inventory});predicates={'tag','original_tag','is_core_of','has_cosmetic_tag'}
 for rel in files:
  p=ROOT/rel
  if not p.exists():continue
  if rel.startswith('common/units/names_divisions/'):
   nodes=parse(p.read_text('utf-8-sig'));assert all(n.get('for_countries') and {c.key for c in n.get('for_countries').children}<=RETIRED for n in nodes)
   changes.append({'file':rel,'action':'empty override suppressing native retired-only division name groups','groups':len(nodes)});p.write_text('# Retired South Asian identity; empty override suppresses the vanilla file.\n','utf-8');continue
  t=p.read_text('utf-8-sig');nodes=parse(t);edits=[];count=0
  def visit(items,parents):
   nonlocal count
   for n in items:
    value=n.value.strip('"') if n.value else None
    if n.key in RETIRED:
     assert not parents or n.op=='',('Unexpected retired country key context',rel,n.key,[v.key for v in parents])
     edits.append((n.start,n.end,''));count+=1;continue
    if value in RETIRED:
     assert n.key in predicates,('Review retired country value',rel,n.key,value)
     edits.append((n.start,n.end,'always = no'));count+=1;continue
    visit(n.children,parents+[n])
  visit(nodes,[])
  if edits:
   replacement=patches(t,edits)
   # Occupation laws are engine entry points: retain the complete law database.
   # Retired-country predicates simply become false; no generic law is removed.
   if rel=='common/occupation_laws/occupation_laws.txt':assert [n.key for n in nodes]==[n.key for n in parse(replacement)]
   if rel.startswith('common/scripted_'):assert [n.key for n in nodes]==[n.key for n in parse(replacement)]
   p.write_text(replacement,'utf-8');changes.append({'file':rel,'action':'remove registration/name blocks or replace only retired predicates with false','references':count})
 dump(OUT/'retired-reference-cleanup.json',changes)

def apply():
 plan=json.loads((OUT/'country-plan.json').read_text('utf-8'));target=json.loads((OUT/'political-target.json').read_text('utf-8'));oldreg={};changed_states=[]
 with zipfile.ZipFile(BACKUP/'project-before.zip') as archive:
  before_pol=json.loads(archive.read('tools/map_maintenance/baseline/initial_territories.json'))
  for name in archive.namelist():
   if name.startswith('common/country_tags/') and name.endswith('.txt'):
    oldreg.update({n.key:n.value.strip('"') for n in parse(archive.read(name).decode('utf-8-sig')) if n.value})
 for sid,(p,t,s) in states().items():
  h=s.get('history');want=target[str(sid)];current={'owner':h.val('owner'),'controller':h.val('controller',h.val('owner')),'cores':sorted({n.value.strip('"') for n in h.children if n.key=='add_core_of'}),'claims':sorted({n.value.strip('"') for n in h.children if n.key=='add_claim_by'})}
  if current==want:
   if before_pol[str(sid)]!=want:changed_states.append({'state':sid,'file':p.relative_to(ROOT).as_posix(),'before':before_pol[str(sid)],'after':want})
   continue
  edits=[(n.start,n.end,'') for n in h.children if n.key in {'owner','controller','add_core_of','add_claim_by'}]
  body='\n\t\towner = '+want['owner']+'\n\t\tcontroller = '+want['controller']+'\n'+''.join('\t\tadd_core_of = '+v+'\n' for v in want['cores'])+''.join('\t\tadd_claim_by = '+v+'\n' for v in want['claims'])
  edits.append((h.value_start+1,h.value_start+1,body));new=patches(t,edits);sn=parse(new)[0]
  assert [canon(n) for n in s.children if n.key!='history']==[canon(n) for n in sn.children if n.key!='history']
  assert [canon(n) for n in h.children if n.key not in {'owner','controller','add_core_of','add_claim_by'}]==[canon(n) for n in sn.get('history').children if n.key not in {'owner','controller','add_core_of','add_claim_by'}]
  p.write_text(new,'utf-8');changed_states.append({'state':sid,'file':p.relative_to(ROOT).as_posix(),'before':before_pol[str(sid)],'after':want})
 clean_retired_references()
 remaining=registry();removed=[]
 for tag in sorted(RETIRED & oldreg.keys()):
  assert tag not in remaining
  for p in (ROOT/'history/countries').glob(tag+'*.txt'):
   assert p.name[:3]==tag and p.name[3] in ' -'
   removed.append({'tag':tag,'file':p.relative_to(ROOT).as_posix(),'kind':'retired country history'});p.unlink()
  # A few old filenames do not have spaces around their hyphen.
  for p in (ROOT/'history/countries').glob(tag+'-*'):
   removed.append({'tag':tag,'file':p.relative_to(ROOT).as_posix(),'kind':'retired country history'});p.unlink()
  rel=oldreg[tag];p=ROOT/'common'/rel
  if p.exists() and rel not in remaining.values():removed.append({'tag':tag,'file':p.relative_to(ROOT).as_posix(),'kind':'retired unshared definition'});p.unlink()
 registry_lines=[];history_changes=[];color_edits={}
 for tag,d in plan.items():
  rgb=' '.join(map(str,d['rgb']))
  if tag in NEW:
   rel=f'countries/APDC_south_asia_{tag}.txt';registry_lines.append(f'{tag} = "{rel}"\n');p=ROOT/'common'/rel
   p.write_text('graphical_culture = commonwealth_gfx\ngraphical_culture_2d = commonwealth_2d\ncolor = rgb { '+rgb+' }\n','utf-8')
   hist=ROOT/'history/countries'/f'{tag} - APDC South Asia.txt'
   hist.write_text('# Minimal playable placeholder; formal politics and leaders are deferred.\nset_technology = { APDC_land_units_bootstrap = 1 }\nset_oob = "APDC_empty"\ncapital = '+str(d['capital'])+'\nset_politics = { ruling_party = authoritarianism elections_allowed = no }\nset_popularities = { authoritarianism = 100 }\n','utf-8')
   history_changes.append({'tag':tag,'file':hist.relative_to(ROOT).as_posix(),'new':True,'capital':d['capital'],'politics':'generic valid placeholder, not a final ideology decision','leaders':'not created or imported'})
  else:
   p=ROOT/'common'/oldreg[tag];source=p if p.exists() else GAME/'common'/oldreg[tag];t=source.read_text('utf-8-sig');matches=list(re.finditer(r'\bcolor\s*=\s*(?:(?:rgb|hsv)\s*)?\{[^{}]*\}',t));assert len(matches)==1,(tag,source);n=matches[0];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t[:n.start()]+'color = rgb { '+rgb+' }'+t[n.end():],'utf-8')
   histories=list((ROOT/'history/countries').glob(tag+' - *.txt'))+list((ROOT/'history/countries').glob(tag+'-*'));histories=list(dict.fromkeys(histories));assert len(histories)==1,(tag,histories)
   hist=histories[0];t=hist.read_text('utf-8-sig');nodes=parse(t);caps=[n for n in nodes if n.key=='capital'];assert len(caps)==1
   if int(caps[0].value)!=d['capital']:
    replacement=patches(t,[(caps[0].value_start,caps[0].value_end,str(d['capital']))]);assert [canon(n) for n in nodes if n.key!='capital']==[canon(n) for n in parse(replacement) if n.key!='capital'];hist.write_text(replacement,'utf-8');history_changes.append({'tag':tag,'file':hist.relative_to(ROOT).as_posix(),'new':False,'capital_before':int(caps[0].value),'capital_after':d['capital'],'other_history_preserved':True})
  color_edits[tag]=rgb
 (ROOT/'common/country_tags/04_apdc_south_asia.txt').write_text('# NEW MAP dynamic-to-formal mapping; only genuinely new IDs are registered here.\n'+''.join(registry_lines),'utf-8')
 p=ROOT/'common/countries/colors.txt';t=p.read_text('utf-8-sig');nodes=parse(t);edits=[];found=set()
 for n in nodes:
  if n.key in color_edits:
   rgb=color_edits[n.key];edits.append((n.start,n.end,n.key+' = { color = rgb { '+rgb+' } color_ui = rgb { '+rgb+' } }'));found.add(n.key)
 new=patches(t,edits)+'\n'+''.join(tag+' = { color = rgb { '+color_edits[tag]+' } color_ui = rgb { '+color_edits[tag]+' } }\n' for tag in color_edits.keys()-found);p.write_text(new,'utf-8')
 country_localisation(plan);canonicalize_country_localisation();random_name_pools()
 dump(BASE/'initial_territories.json',target);dump(BASE/'south_asia_identity_20261102.json',{'source_save_sha256':sha(Path(META['source_save'])),'dynamic_to_formal':{d['dynamic']:tag for tag,d in plan.items()},'reused_native_tags':[tag for tag in plan if tag not in NEW],'new_tags':sorted(NEW),'retired_tags':sorted(RETIRED),'country_plan':'docs/map-maintenance/20261102-south-asia/country-plan.json','territorial_authority':'tools/map_maintenance/baseline/initial_territories.json','prior_GF_mapping_is_historical':'The 2026-10-21 RAJ/PAK→PAK merger no longer describes current South Asian identities. Do not reapply it.'})
 with zipfile.ZipFile(BACKUP/'project-before.zip') as archive:
  original_names=set(archive.namelist())
  for tag in sorted(RETIRED & oldreg.keys()):
   for name in original_names:
    if name.startswith('history/countries/'+tag) and name.endswith('.txt') and not(ROOT/name).exists() and not any(x['file']==name for x in removed):removed.append({'tag':tag,'file':name,'kind':'retired country history'})
   name='common/'+oldreg[tag]
   if name in original_names and not(ROOT/name).exists() and not any(x['file']==name for x in removed):removed.append({'tag':tag,'file':name,'kind':'retired unshared definition'})
 dump(OUT/'state-changes.json',changed_states);dump(OUT/'country-history-changes.json',history_changes);dump(OUT/'retired-country-files.json',removed);dump(OUT/'political-relations.json',target)
 print(json.dumps({'states_changed':len(changed_states),'histories_changed':history_changes,'retired_files':len(removed),'new_tags':sorted(NEW),'native_reused':len(plan)-len(NEW)},ensure_ascii=False))

def country_localisation(plan):
 order=list(plan)
 names={
 'simp_chinese':[d['name'] for d in plan.values()],
 'english':[d['english'] for d in plan.values()],
 'french':["République de l'Inde","République populaire islamique du Pakistan","Armée de libération du Pendjab","République du Gujarat","République marathe","République du Karnataka","République des Maldives","République populaire du Kerala","République socialiste démocratique du Sri Lanka","État tamoul","République de l'Andhra","Armée populaire de libération de l'Inde","République populaire du Bengale","République de l'Assam"],
 'german':['Republik Indien','Islamische Volksrepublik Pakistan','Befreiungsarmee des Punjab','Republik Gujarat','Marathische Republik','Republik Karnataka','Republik Malediven','Volksrepublik Kerala','Demokratische Sozialistische Republik Sri Lanka','Tamilischer Staat','Republik Andhra','Indische Volksbefreiungsarmee','Volksrepublik Bengalen','Republik Assam'],
 'spanish':['República de la India','República Popular Islámica de Pakistán','Ejército de Liberación del Punyab','República de Guyarat','República maratí','República de Karnataka','República de Maldivas','República Popular de Kerala','República Socialista Democrática de Sri Lanka','Estado tamil','República de Andhra','Ejército Popular de Liberación de la India','República Popular de Bengala','República de Assam'],
 'braz_por':['República da Índia','República Popular Islâmica do Paquistão','Exército de Libertação do Punjab','República de Guzerate','República Marata','República de Carnataca','República das Maldivas','República Popular de Querala','República Democrática Socialista do Sri Lanka','Estado Tâmil','República de Andhra','Exército Popular de Libertação da Índia','República Popular de Bengala','República de Assam'],
 'polish':['Republika Indii','Islamska Ludowa Republika Pakistanu','Armia Wyzwolenia Pendżabu','Republika Gudźaratu','Republika Marathów','Republika Karnataki','Republika Malediwów','Ludowa Republika Kerali','Demokratyczno-Socjalistyczna Republika Sri Lanki','Państwo Tamilskie','Republika Andhry','Indyjska Ludowa Armia Wyzwolenia','Ludowa Republika Bengalu','Republika Asamu'],
 'russian':['Республика Индия','Исламская Народная Республика Пакистан','Освободительная армия Пенджаба','Республика Гуджарат','Маратхская Республика','Республика Карнатака','Мальдивская Республика','Народная Республика Керала','Демократическая Социалистическая Республика Шри-Ланка','Тамильское государство','Республика Андхра','Индийская народно-освободительная армия','Народная Республика Бенгалия','Республика Ассам'],
 'japanese':['インド共和国','パキスタン・イスラム人民共和国','パンジャーブ解放軍','グジャラート共和国','マラーター共和国','カルナータカ共和国','モルディブ共和国','ケーララ人民共和国','スリランカ民主社会主義共和国','タミル国','アーンドラ共和国','インド人民解放軍','ベンガル人民共和国','アッサム共和国'],
 'korean':['인도 공화국','파키스탄 이슬람 인민공화국','펀자브 해방군','구자라트 공화국','마라티 공화국','카르나타카 공화국','몰디브 공화국','케랄라 인민공화국','스리랑카 민주사회주의 공화국','타밀국','안드라 공화국','인도 인민해방군','벵골 인민공화국','아삼 공화국'],
 }
 adjectives={
 'simp_chinese':[d['adjective'] for d in plan.values()],
 'english':['Indian','Pakistani','Punjabi','Gujarati','Marathi','Kannada','Maldivian','Keralite','Sri Lankan','Tamil','Andhra','Indian','Bengali','Assamese'],
 'french':['indien','pakistanais','pendjabi','gujarati','marathe','kannada','maldivien','kéralais','sri-lankais','tamoul','andhra','indien','bengali','assamais'],
 'german':['Indisch','Pakistanisch','Punjabisch','Gujaratisch','Marathisch','Kannadisch','Maledivisch','Keralisch','Sri-Lankisch','Tamilisch','Andhra','Indisch','Bengalisch','Assamesisch'],
 'spanish':['indio','pakistaní','punyabí','guyaratí','maratí','kannada','maldivo','keralita','ceilanés','tamil','andhra','indio','bengalí','asamés'],
 'braz_por':['indiano','paquistanês','punjabi','guzerate','marata','canarês','maldivo','queralês','cingalês','tâmil','andhra','indiano','bengali','assamês'],
 'polish':['indyjskie','pakistańskie','pendżabskie','gudźarackie','marackie','kannadyjskie','malediwskie','keralskie','lankijskie','tamilskie','andhryjskie','indyjskie','bengalskie','asamskie'],
 'russian':['Индийск.','Пакистанск.','Пенджабск.','Гуджаратск.','Маратхск.','Карнатакск.','Мальдивск.','Керальск.','Шри-ланкийск.','Тамильск.','Андхрск.','Индийск.','Бенгальск.','Ассамск.'],
 'japanese':['インド','パキスタン','パンジャーブ','グジャラート','マラーター','カルナータカ','モルディブ','ケーララ','スリランカ','タミル','アーンドラ','インド','ベンガル','アッサム'],
 'korean':['인도','파키스탄','펀자브','구자라트','마라티','카르나타카','몰디브','케랄라','스리랑카','타밀','안드라','인도','벵골','아삼'],
 }
 for lang in LANGS:
  entries={}
  for i,tag in enumerate(order):
   assert len(names[lang])==len(adjectives[lang])==14
   for form in [tag]+[tag+'_'+v for v in IDEOLOGIES]+[tag+'_'+v for v in ['democratic','neutrality']]:
    entries[form]=names[lang][i];entries[form+'_DEF']=names[lang][i];entries[form+'_ADJ']=adjectives[lang][i]
  body='l_'+lang+':\n'+''.join(' '+k+':0 "'+v.replace('"','\\"')+'"\n' for k,v in entries.items())
  (ROOT/f'localisation/replace/zzzzzzz_APDC_south_asia_l_{lang}.yml').write_text(body,'utf-8-sig')
 dump(OUT/'country-localisation.json',{'languages':LANGS,'country_order':order,'forms_per_country':12,'entries_per_language':len(entries),'names':names,'political_variant_names_fixed_to_user_identity':True})

def canonicalize_country_localisation():
 # Existing replace files can take precedence over another replace file.
 # Update their exact country-name keys in place, and emit only missing keys.
 report=json.loads((OUT/'country-localisation.json').read_text('utf-8'));changes=[];emitted={}
 for lang in LANGS:
  newfile=ROOT/f'localisation/replace/zzzzzzz_APDC_south_asia_l_{lang}.yml'
  desired=dict(re.findall(r'^ ([A-Za-z0-9_]+):0 "([^"\n]*)"$',newfile.read_text('utf-8-sig'),re.M));assert len(desired)==504
  found=set()
  for p in (ROOT/'localisation').rglob('*.yml'):
   if p==newfile:continue
   t=p.read_text('utf-8-sig')
   if not re.search(r'^\s*l_'+lang+r'\s*:',t,re.M):continue
   touched=[]
   def replace(m):
    key=m[2]
    if key not in desired:return m[0]
    found.add(key)
    if m[4]!=desired[key]:touched.append(key)
    return m[1]+key+m[3]+'"'+desired[key]+'"'+m[5]
   updated=re.sub(r'(?m)^([ \t]*)([A-Za-z0-9_]+)(:\d*\s+)"((?:\\.|[^"\\\n])*)"([^\n]*)$',replace,t)
   if touched:p.write_text(updated,'utf-8-sig');changes.append({'file':p.relative_to(ROOT).as_posix(),'keys':touched})
  missing={k:v for k,v in desired.items() if k not in found};newfile.write_text('l_'+lang+':\n'+''.join(' '+k+':0 "'+v+'"\n' for k,v in missing.items()),'utf-8-sig');emitted[lang]=len(missing)
 report['existing_country_keys_updated_in_place']=True;report['existing_files_changed']=changes;report['new_file_entries_by_language']=emitted
 dump(OUT/'country-localisation.json',report)

def random_name_pools():
 # Registration prerequisite only; leave all fixed characters and portraits alone.
 t=(ROOT/'common/names/00_names.txt').read_text('utf-8-sig');nodes={n.key:n for n in parse(t)}
 body='# Generic random names only; no fixed leaders or portraits are created.\n'
 for tag,src in [('KER','RAS'),('IPL','RAJ'),('ASM','RAJ')]:
  n=nodes[src];body+=tag+t[n.start+len(src):n.end]+'\n'
 (ROOT/'common/names/APDC_south_asia.txt').write_text(body,'utf-8')

if __name__=='__main__':globals()[sys.argv[1]]()
