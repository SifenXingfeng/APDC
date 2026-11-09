"""Reconnect the two reviewed Saint Petersburg railway gaps, retaining all grades."""
from pathlib import Path
import sys,json,re,hashlib,zipfile,shutil,collections
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/unit_overhaul'))
from cw import parse
OUT=ROOT/'docs/map-maintenance/20261027-railways'
BACKUP=Path(json.loads(Path('D:/APDC-railway-reconnect-current.json').read_text('utf-8'))['backup'])
QA=Path('D:/APDC_RailwayQA_20261027_1912')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')

def repair():
    path=ROOT/'map/railways.txt';original=path.read_bytes();before=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'))
    assert sha(path)==before['map/railways.txt'],'Railways changed since backup'
    lines=original.splitlines(keepends=True);changes=[]
    for index,line in enumerate(lines):
        values=list(map(int,line.split())) if line.strip() else []
        if len(values)>4 and values[:4]==[1,20,3151,18261]:
            replacement=line.replace(b'1 20 3151 18261 ',b'1 21 3151 18292 18261 ',1)
        elif len(values)>4 and values[:5]==[1,14,3151,18292,3060]:
            replacement=line.replace(b'1 14 3151 18292 3060 ',b'1 13 3151 3060 ',1)
        else:continue
        assert replacement!=line
        ending=b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
        replacement=replacement.rstrip(b' \t\r\n')+ending
        changes.append({'line':index+1,'before':line.decode().strip(),'after':replacement.decode().strip(),'grade_before':values[0],'grade_after':int(replacement.split()[0])});lines[index]=replacement
    assert [x['line'] for x in changes]==[373,610],changes
    changed=b''.join(lines)
    def graph(data):
        graph={};coverage=set();routes=[]
        for line in data.splitlines():
            if not line.strip():continue
            grade,count,*pids=map(int,line.split());assert len(pids)==count
            coverage.update(pids);routes.append((grade,pids[0],pids[-1]))
            for p,q in zip(pids,pids[1:]):
                key=tuple(sorted((p,q)));graph[key]=max(grade,graph.get(key,0))
        return graph,coverage,routes
    oldgraph,oldcoverage,oldroutes=graph(original);newgraph,newcoverage,newroutes=graph(changed)
    assert oldcoverage==newcoverage and oldroutes==newroutes
    removed=set(oldgraph)-set(newgraph);added=set(newgraph)-set(oldgraph)
    assert removed=={tuple(sorted(x)) for x in [(3151,18261),(18292,3060)]}
    assert added=={tuple(sorted(x)) for x in [(18292,18261),(3151,3060)]}
    assert all(newgraph[k]==oldgraph[k] for k in oldgraph.keys()&newgraph.keys())
    assert all(newgraph[k]==1 for k in added) and newgraph[tuple(sorted((3151,18292)))]==1
    for row in changes:
        pids=list(map(int,row['after'].split()))[2:];assert len(pids)==len(set(pids)),('modified route revisits province',pids)
    path.write_bytes(changed)
    dump(OUT/'repair.json',{'backup':str(BACKUP),'file':'map/railways.txt','before_sha256':hashlib.sha256(original).hexdigest(),'after_sha256':sha(path),'changes':changes,'removed_non_adjacent_edges':sorted(removed),'added_adjacent_edges':sorted(added),'all_previous_valid_edges_and_grades_preserved':True,'province_coverage_unchanged':True,'route_endpoints_unchanged':True,'loops_introduced':False})
    # Full current geography audit, with reports isolated from the earlier checkpoint.
    sys.path.insert(0,str(ROOT/'tools/map_maintenance'));import finish_20261027 as maintenance
    maintenance.OUT=OUT;maintenance.audit()
    report=json.loads((OUT/'static-audit.json').read_text('utf-8'))
    assert not report['observations']['rail_adjacency_gaps']
    print(json.dumps({'changed_lines':changes,'global_railway_gaps':0}))

def prepare():
    assert not QA.exists();(QA/'mod').mkdir(parents=True);driver=QA/'driver'
    for rel in ['common/on_actions','common/defines']:(driver/rel).mkdir(parents=True)
    desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M)
    (QA/'mod/APDC.mod').write_text(desc,'utf-8')
    (QA/'mod/APDC_RailwayQA.mod').write_text('name="APDC railway diagnostics"\npath="'+driver.as_posix()+'"\nsupported_version="1.19.*"\n','utf-8')
    dump(QA/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_RailwayQA.mod'],'disabled_dlcs':[]})
    shutil.copy2('D:/APDC_MapFinishQA_20261027/settings.txt',QA/'settings.txt')
    (driver/'common/defines/zzzz_APDC_railway_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf-8')
    (driver/'common/on_actions/zzzz_APDC_railway_qa.txt').write_text('on_actions = { on_daily_GER = { effect = { log = "APDC_RAILWAY_QA DAY date=[GetDateText]" } } }\n','utf-8')
    user=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV');files=[]
    for name in ['dlc_load.json','settings.txt','continue_game.json','last_save']:
        p=user/name
        if p.is_file():files.append(p)
    files.extend(p for p in (user/'save games').glob('*') if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower()))
    dump(OUT/'qa-preparation.json',{'profile':str(QA),'user_file_hashes':{str(p):sha(p) for p in files},'disabled_dlcs':[],'toolpack_loaded':False,'scene':'GER 2060 ordinary start; isolated logging driver'})
    print(str(QA))

def extract(text,name):
    m=re.search(r'(?m)^'+name+r'=\{',text);assert m;start=m.end();depth=1
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if depth==0:return text[start:start+token.start()]
    raise ValueError(name)

def verify():
    save=QA/'save games/autosave.hoi4';text=save.read_text('utf-8-sig');date=re.search(r'(?m)^date="([^"]+)"',text).group(1)
    native=next(n for n in parse(extract(text,'rail_way')) if n.key=='rail_way');nodes={int(n.key):n for n in native.children}
    oldtext=Path('D:/APDC_MapFinishQA_20261027/save games/autosave.hoi4').read_text('utf-8-sig')
    oldnative=next(n for n in parse(extract(oldtext,'rail_way')) if n.key=='rail_way');oldnodes={int(n.key):n for n in oldnative.children}
    comparisons=[]
    for pid in [3151,18292,18261,3060]:
        old=[int(n.key) for n in oldnodes[pid].get('rail_way').children];new=[int(n.key) for n in nodes[pid].get('rail_way').children]
        assert len(old)==len(new),(pid,old,new)
        changes=[{'neighbor_slot':i,'before':a,'after':b} for i,(a,b) in enumerate(zip(old,new)) if a!=b]
        assert len(changes)==1 and changes[0]['before']==0 and changes[0]['after']==1,(pid,changes,old,new)
        comparisons.append({'province':pid,'before':old,'after':new,'changes':changes})
    state_nodes=parse(extract(text,'states'));states={int(n.key):n for n in state_nodes}
    assert len(states)==1558
    expected=json.loads((ROOT/'tools/map_maintenance/baseline/initial_territories.json').read_text('utf-8'));cores=collections.defaultdict(list);claims=collections.defaultdict(list)
    for match in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',extract(text,'countries')):
        tag,body=match.groups()
        for key,target in [('cores',cores),('claims',claims)]:
            m=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
            if m:
                for sid in map(int,re.findall(r'\d+',m.group(1))):target[sid].append(tag)
    differences=[]
    for sid,n in states.items():
        got={'owner':n.val('owner'),'controller':n.val('controller',n.val('owner')),'cores':sorted(cores[sid]),'claims':sorted(claims[sid])}
        row=expected[str(sid)];want={**row,'cores':sorted(row['cores']),'claims':sorted(row['claims'])}
        if got!=want:differences.append({'state':sid,'actual':got,'expected':want})
    err=(QA/'logs/error.log').read_text('utf-8-sig',errors='replace');relevant=[s for s in err.splitlines() if re.search(r'MAP_ERROR|(?:railway|Railway)|Province with id:|State \d+ has no|APDC_RailwayQA|APDC_railway_qa',s)]
    stop=json.loads((QA/'silent-stop.json').read_text('utf-8-sig'));prep=json.loads((OUT/'qa-preparation.json').read_text('utf-8'))
    altered=[p for p,digest in prep['user_file_hashes'].items() if sha(Path(p))!=digest]
    passed=not differences and not relevant and not altered and date.startswith('2060.2.') and not stop['still_running'] and not stop['steam_app_running'] and not stop['remaining_helpers']
    report={'passed':passed,'date':date,'save_sha256':sha(save),'native_railway_vectors':comparisons,'meaning':'One new grade-1 native adjacency at each endpoint of the two repaired edges; all other native edge levels unchanged. Engine neighbor slots compared with the previous same-topology save.','states_checked':len(states),'relation_differences':differences,'map_or_railway_errors':relevant,'user_files_changed':altered,'process':json.loads((QA/'silent-process.json').read_text('utf-8-sig')),'stop':stop,'enabled_mods':json.loads((QA/'dlc_load.json').read_text('utf-8'))}
    dump(OUT/'runtime-audit.json',report)
    with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in (QA/'logs').glob('*'):
            if p.is_file():z.write(p,'logs/'+p.name)
        for name in ['silent-process.json','silent-stop.json','settings.txt','dlc_load.json']:z.write(QA/name,name)
    assert passed,report
    print(json.dumps({'passed':True,'date':date,'native_endpoints_verified':4,'relation_differences':0,'map_or_railway_errors':0,'game_closed':True}))

def checkpoint():
    from concurrent.futures import ThreadPoolExecutor
    runtime=json.loads((OUT/'runtime-audit.json').read_text('utf-8'));assert runtime['passed']
    current=ROOT/'tools/map_maintenance/baseline/latest_checkpoint.json'
    with zipfile.ZipFile(BACKUP/'before.zip') as z:prior=json.loads(z.read('tools/map_maintenance/baseline/latest_checkpoint.json'))
    dump(OUT/'previous-checkpoint.json',prior)
    snapshot=OUT/'railways-checkpoint.txt';shutil.copy2(ROOT/'map/railways.txt',snapshot)
    latest={**prior,'previous_report':prior['report'],'report':'docs/map-maintenance/20261027-railways','geography_backup':prior['backup'],'backup':str(BACKUP),'railways':'map/railways.txt','railways_sha256':sha(snapshot),'railways_checkpoint':'docs/map-maintenance/20261027-railways/railways-checkpoint.txt','runtime':'2060.2.1.1 GER; all 1558 state relations match; four railway endpoint vectors each gain exactly one grade-1 edge; test process cleaned up'}
    dump(current,latest)
    before=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'))
    files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts and p!=OUT/'preservation-audit.json']
    def record(p):return p.relative_to(ROOT).as_posix(),sha(p)
    with ThreadPoolExecutor(max_workers=8) as pool:after=dict(pool.map(record,files))
    changed=[{'file':rel,'before':before[rel],'after':digest} for rel,digest in after.items() if rel in before and before[rel]!=digest]
    added=[{'file':rel,'after':digest} for rel,digest in after.items() if rel not in before]
    removed=sorted(set(before)-set(after))
    allowed={'map/railways.txt','tools/map_maintenance/baseline/latest_checkpoint.json','tools/map_maintenance/repair_railways_20261027.py'}
    unexpected=[row for row in changed+added if row['file'] not in allowed and not row['file'].startswith('docs/map-maintenance/20261027-railways/')]
    report={'passed':not removed and not unexpected,'files_hashed':len(after),'changed_existing':changed,'added':added,'removed':removed,'unexpected':unexpected,'pre_existing_dirty_files_preserved':True,'state_history_and_cold_war_map_bytes_unchanged':True,'cache_git_and_own_manifest_excluded':True}
    dump(OUT/'preservation-audit.json',report);assert report['passed'],report
    print(json.dumps({'passed':True,'files_hashed':len(after),'changed_existing':len(changed),'unexpected':len(unexpected),'removed':len(removed)}))

if __name__=='__main__':{'repair':repair,'prepare':prepare,'verify':verify,'checkpoint':checkpoint}[sys.argv[1]]()
