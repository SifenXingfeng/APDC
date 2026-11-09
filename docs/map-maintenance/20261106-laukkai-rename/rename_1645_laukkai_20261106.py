"""Name-only update after the user's final answer. No map audit or game launch."""
from pathlib import Path
import datetime,hashlib,json,re,zipfile,sys,shutil
sys.stdout.reconfigure(encoding='utf8')
ROOT=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/APDC').resolve()
USER=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
BASE=ROOT/'tools/map_maintenance/baseline'
OUT=ROOT/'docs/map-maintenance/20261106-laukkai-rename'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
assert not OUT.exists(),'This dated rename is a one-time operation; inspect the completed report instead.'
cp=json.loads((BASE/'latest_checkpoint.json').read_text('utf8'))
assert cp['report']=='docs/map-maintenance/20261106',cp['report']
src=ROOT/'history/states/1645-Gongsang.txt';dest=src.with_name('1645-Laukkai.txt')
assert src.is_file() and not dest.exists()
assert src.parent.resolve()==dest.parent.resolve()==(ROOT/'history/states').resolve()
state_raw=src.read_bytes();assert re.search(rb'\bid\s*=\s*1645\b',state_raw)
assert re.search(rb'provinces\s*=\s*\{\s*4210\s*\}',state_raw)
city=json.loads((BASE/'modern_victory_points.json').read_text('utf8'))['province_id_inventory']['4210']
assert city['state_id']==1645 and city['names']['simp_chinese']=='老街' and city['names']['english']=='Laukkai'
names=city['names'];assert len(names)==10
alias=re.compile(r'^(?:STATE_(\d+)|[A-Za-z0-9_]+_STATE_(\d+)|STATE_(\d+)_[A-Za-z0-9_]+|state_(\d+)_name|(\d+)_[A-Za-z0-9_]+_name)$')
edits={};loc_changes=[]
for lang in names:
 for p in (ROOT/'localisation').rglob('*_l_'+lang+'.yml'):
  text=p.read_text('utf-8-sig');lines=text.splitlines(keepends=True);touched=False
  for i,line in enumerate(lines):
   m=re.match(r'^(\s*)([A-Za-z0-9_.-]+):(-?\d+)\s+"((?:\\.|[^"\\])*)"(.*?)(\r?\n)?$',line)
   if not m:continue
   a=alias.fullmatch(m[2])
   if not a or int(next(v for v in a.groups() if v))!=1645 or '[' in m[4]:continue
   if m[4]==names[lang] and m[3]=='0':continue
   lines[i]=m[1]+m[2]+':0 "'+names[lang]+'"'+m[5]+'\n';touched=True
   loc_changes.append({'file':p.relative_to(ROOT).as_posix(),'language':lang,'key':m[2],'before':m[4],'after':names[lang]})
  if touched:edits[p]=''.join(lines).encode('utf-8-sig')
assert {r['language'] for r in loc_changes}==set(names)
editor=USER/'localisation/simp_chinese/state_names_l_simp_chinese.yml'
text=editor.read_text('utf-8-sig');text,n=re.subn(r'(?m)^(\s*STATE_1645):-?\d+\s+"[^"\n]*"',lambda m:m[1]+':0 "老街"',text);assert n==1
edits[editor]=text.encode('utf-8-sig')
index=json.loads((BASE/'current_state_files.json').read_text('utf8'));assert index['1645']==src.name
index['1645']=dest.name;edits[BASE/'current_state_files.json']=(json.dumps(index,ensure_ascii=False,indent=2)+'\n').encode('utf8')
tool=ROOT/'tools/map_maintenance/finish_20261106.py';text=tool.read_text('utf8')
old="1645:['贡桑','Gongsang','Гунсан','ゴンサン','궁상']"
new="1645:"+repr([names[k] for k in ['simp_chinese','english','russian','japanese','korean']])
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("'gongsang':'Project adopts Gongsang as the pinyin transliteration of the user-provided 贡桑 pending an optional official-English spelling response; not identified with Kokang or a claimed official modern placename. Russian/Japanese/Korean are project phonetic forms. Laukkai city name remains unchanged.'", "'laukkai':'The user confirmed state 1645 as 老街 / Laukkai after the closeout; all languages inherit the existing city names. See docs/map-maintenance/20261106-laukkai-rename.'")
# Keep the dated report writer from regenerating obsolete active-name guidance.
text=text.replace('新增1645“贡桑”','新增1645“老街”').replace('新增贡桑1645','新增老街1645')
text=text.replace('用户未提供贡桑的正式拉丁拼写；已异步询问并在继续工作时说明暂采用拼音Gongsang，俄/日/韩为项目音译。此名称未被擅自改成Kokang，也不冒称已核实的现代正式地名。正式拼写后续可仅作名称修改，无需重跑地块验收。','用户随后确认1645改名为老街 / Laukkai，十语沿用现有老街城市译名；详见20261106-laukkai-rename。此次仅改名，免重复地图测试和游戏启动。')
text=text.replace('贡桑拉丁拼写暂采用项目音译Gongsang。','1645已按用户后续回复正式改为老街 / Laukkai，最新名称检查点为20261106-laukkai-rename。')
edits[tool]=text.encode('utf8')
handover=[ROOT/p for p in ['项目接手文档/00_快速接手/新对话接手指南.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/02_系统维护/地图与版本兼容_维护.md','项目接手文档/02_系统维护/冷战系统_规则与维护.md','项目接手文档/05_参数与历史档案/对话任务总账.md']]
note='2026-11-06名称确认：用户后续指定1645为老街 / Laukkai，取代临时贡桑 / Gongsang；十语、正式文件名和当前州索引已同步。最新名称检查点为20261106-laukkai-rename，继承同日已通过的地块/冷战/实际开局证据。仅改名，按AGENTS免地图静态测试及游戏启动。详见[老街改名记录](../../docs/map-maintenance/20261106-laukkai-rename/README.md)。'
for p in handover:
 text=p.read_text('utf8');at=text.find('\n')+1;text=text[:at]+'\n'+note+'\n'+text[at:]
 text=text.replace('新增贡桑1645','新增老街1645').replace('新增1645贡桑','新增1645老街').replace('新增贡桑、','新增老街、')
 text=text.replace('贡桑拉丁拼写暂采用项目音译Gongsang。','老街名称已按后续用户回复确认。')
 text=text.replace('latest_checkpoint.json现指向20261106，','latest_checkpoint.json现指向20261106-laukkai-rename，').replace('当前指向20261106 |','当前指向20261106-laukkai-rename |')
 if p.name=='地图与版本兼容_维护.md':
  lines=text.splitlines(keepends=True)
  for i,line in enumerate(lines):
   if line.startswith('| 最新州原字节归档 |'):lines[i]=line.replace('/20261106/states-checkpoint.zip','/20261106-laukkai-rename/states-checkpoint.zip')
  text=''.join(lines)
 edits[p]=text.encode('utf8')
city_review={'date':'2026-11-06','state':1645,'name':'老街','english':'Laukkai','province':4210,'contains_named_city':True,'city_inventory':'tools/map_maintenance/baseline/modern_victory_points.json#province_id_inventory.4210','names':names,'province_list_unchanged':True,'victory_point_score_unchanged':city['score']}
mismatches=json.loads((BASE/'city_named_state_mismatches.json').read_text('utf8'));mismatches['latest_name_only_review']={**city_review,'report':OUT.relative_to(ROOT).as_posix()+'/city-review.json'}
edits[BASE/'city_named_state_mismatches.json']=(json.dumps(mismatches,ensure_ascii=False,indent=2)+'\n').encode('utf8')
# Targeted byte backup, preserving previous completed reports and archives.
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')
backup=ROOT.parent/'.codex_backups/APDC'/(stamp+'-1645-laukkai-name-only');backup.mkdir(parents=True,exist_ok=False)
targets=set(edits)|{src,BASE/'latest_checkpoint.json'}
before={str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in targets}
state_before={p.name:sha(p) for p in (ROOT/'history/states').glob('*.txt')}
protected=[BASE/'initial_territories.json',BASE/'modern_victory_points.json',ROOT/'docs/cold-war/20261024/geometry.json',ROOT/'map/buildings.txt',ROOT/'map/railways.txt']
protected_before={str(p):sha(p) for p in protected}
with zipfile.ZipFile(backup/'files-before.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(targets):z.write(p,('project/'+p.relative_to(ROOT).as_posix()) if p.is_relative_to(ROOT) else 'user/'+p.relative_to(USER).as_posix())
dump(backup/'manifest-before.json',before);dump(backup/'states-before.json',state_before)
(backup/'user-request.txt').write_text('那就叫老街，中文名也改成老街\n','utf8')
OUT.mkdir(parents=True)
for p,data in edits.items():p.write_bytes(data)
src.rename(dest);assert dest.read_bytes()==state_raw
shutil.copy2(Path(__file__),OUT/'rename_1645_laukkai_20261106.py')
# Check names and necessary references only; no map static test or game run.
for lang in names:
 p=ROOT/f'localisation/replace/zzzz_apdc_map_geography_l_{lang}.yml';raw=p.read_bytes();assert raw.startswith(b'\xef\xbb\xbf')
 values=re.findall(r'(?m)^\s*STATE_1645:0\s+"([^"\n]*)"',raw.decode('utf-8-sig'));assert values==[names[lang]],(lang,values)
assert 'STATE_1645:0 "老街"' in editor.read_text('utf-8-sig')
assert json.loads((BASE/'current_state_files.json').read_text('utf8'))['1645']=='1645-Laukkai.txt'
state_after={p.name:sha(p) for p in (ROOT/'history/states').glob('*.txt')}
assert state_after=={(dest.name if p==src.name else p):h for p,h in state_before.items()}
assert all(sha(Path(p))==h for p,h in protected_before.items())
dump(OUT/'name-decisions.json',{'state':1645,'previous_chinese':'贡桑','previous_english':'Gongsang','confirmed_chinese':'老街','confirmed_english':'Laukkai','names':names,'source':'Explicit user reply; non-Chinese forms from the existing verified city inventory; no new city names or score'})
dump(OUT/'renames.json',[{'state':1645,'old':src.relative_to(ROOT).as_posix(),'new':dest.relative_to(ROOT).as_posix(),'bytes_unchanged':True,'sha256':sha(dest)}]);dump(OUT/'localisation-changes.json',loc_changes);dump(OUT/'city-review.json',city_review)
dump(OUT/'state-index.json',index)
archive=OUT/'states-checkpoint.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted((ROOT/'history/states').glob('*.txt')):z.write(p,p.name)
dump(OUT/'state-hashes.json',{p.name:{'sha256':sha(p)} for p in (ROOT/'history/states').glob('*.txt')})
ma=OUT/'map-checkpoint.zip'
with zipfile.ZipFile(ROOT/cp['map_checkpoint_archive']) as original,zipfile.ZipFile(ma,'w',zipfile.ZIP_DEFLATED) as z:
 for name in original.namelist():z.writestr(name,(BASE/'current_state_files.json').read_bytes() if name=='tools/map_maintenance/baseline/current_state_files.json' else original.read(name))
newcp={**cp,'report':OUT.relative_to(ROOT).as_posix(),'previous_report':cp['report'],'state_history_archive':archive.relative_to(ROOT).as_posix(),'state_history_sha256':sha(archive),'map_checkpoint_archive':ma.relative_to(ROOT).as_posix(),'map_checkpoint_sha256':sha(ma),'city_review':OUT.relative_to(ROOT).as_posix()+'/city-review.json','latest_change_backup':str(backup),'name_only':True,'name_only_validation':OUT.relative_to(ROOT).as_posix()+'/name-reference-audit.json','runtime_evidence_inherited_from':cp['report'],'runtime':'Inherited unchanged geography: '+cp['runtime']+'; subsequent state 1645 name-only rename, no new game required'}
dump(BASE/'latest_checkpoint.json',newcp)
dump(OUT/'name-reference-audit.json',{'passed':True,'states_checked_for_byte_preservation':len(state_after),'state_file_content_unchanged':True,'ten_languages_checked':list(names),'all_matching_geographic_aliases_updated':True,'state_1645_contains_city_province_4210':True,'filename_index_checkpoint_synced':True,'politics_economy_city_inventory_cold_war_geometry_buildings_railways_byte_preserved':protected_before,'map_static_tests_run':False,'game_launched':False,'reason':'AGENTS exempts name-only work; the completed geography/runtime/visual evidence is inherited','old_report_preserved':cp['report'],'backup':str(backup)})
readme='''# 2026-11-06 老街州名称确认

用户后续回复“那就叫老街，中文名也改成老街”。1645正式改为老街 / Laukkai，取代此前临时贡桑 / Gongsang。十语州名沿用现有老街城市译名，1645-Gongsang.txt改为1645-Laukkai.txt，文件内容保持原字节；当前路径索引、维护工具的1645配置、编辑器中文名称及接手资料同步。

1645仍包含4210老街城市地块、BRM归属/控制/核心及原有人口、资源、建筑和1分胜利点。仅核对名称、别名、文件名和必要引用，不运行地图静态测试或启动游戏。冷战使用稳定州ID和动态拥有国名称，无须重建几何。全部州文件内容哈希与此前一致，政治快照、城市清单、冷战几何、模型建筑及铁路字节不变。

新states-checkpoint.zip使用当前正式文件名；map-checkpoint.zip仅更新其中的当前州路径索引。上一轮报告及归档保持历史原貌；最新检查点继承上轮GER 2060.2.1.1的1645州核对和冷战世界/BRM/返回画面证据，未将本次改名写成新运行验收。最新检查点的backup/geography_backup继续指向原有完整地理/运行证据，latest_change_backup另指本次窄备份。

名称与引用检查见name-reference-audit.json，十语见name-decisions.json。原字节备份：BACKUP_PATH。
'''.replace('BACKUP_PATH',backup.as_posix())
(OUT/'README.md').write_text(readme,'utf8')
dump(OUT/'file-changes.json',[{'file':str(p),'before':before[str(p)]['sha256'],'after':sha(dest if p==src else p)} for p in sorted(targets)])
print(json.dumps({'renamed':str(dest),'languages':len(names),'state_content_unchanged':True,'checkpoint':str(BASE/'latest_checkpoint.json'),'backup':str(backup),'game_run':False},ensure_ascii=False))
