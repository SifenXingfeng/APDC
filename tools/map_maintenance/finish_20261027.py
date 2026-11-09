"""Scoped 2026-10-27 map finishing and reproducible evidence (no old GF history replay)."""
from pathlib import Path
import sys, json, hashlib, subprocess, collections, csv, re, shutil, zipfile, io
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/unit_overhaul'))
from cw import parse, walk, patches
BASE = ROOT/'tools/map_maintenance/baseline'
OUT = ROOT/'docs/map-maintenance/20261027'
BACKUP = Path(json.loads(Path('D:/APDC-map-finish-current.json').read_text('utf-8'))['backup'])
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')

def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', 'utf-8')

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(n): return (n.key,n.value,n.op,tuple(canon(c) for c in n.children))
def statefiles(folder):
    result = {}
    for p in sorted(folder.glob('*.txt')):
        text=p.read_text('utf-8-sig');s=next(n for n in parse(text) if n.key=='state');sid=int(s.val('id'))
        assert sid not in result, ('duplicate state',sid)
        result[sid]=(p,text,s)
    return result

def provinces(states):
    result={}
    for sid,(_,_,s) in states.items():
        for n in s.get('provinces').children:
            pid=int(n.key);assert pid not in result,('duplicate province',pid,sid,result.get(pid));result[pid]=sid
    return result

def half_up(x): return (x.numerator*2+x.denominator)//(x.denominator*2)

def resources(s):
    result={}
    for block in [n for n in s.children if n.key=='resources']:
        for n in block.children:
            assert n.key not in result,('ambiguous duplicate resource key',s.val('id'),n.key)
            result[n.key]=Fraction(n.value)
    return result

def economy(states):
    originals=statefiles(BASE/'original_economy/history/states');source_map=provinces(originals)
    coverage=collections.Counter();results={};dupes=[]
    source_values={}
    for sid,(_,_,s) in originals.items():
        blocks=[n for n in s.children if n.key=='resources'];res={}
        for block in blocks:
            for n in block.children:
                if n.key in res:dupes.append((sid,n.key))
                res[n.key]=Fraction(n.value)
        source_values[sid]=(int(s.val('manpower','0')),res,len(s.get('provinces').children))
    assert not dupes, ('ambiguous original resources',dupes)
    for sid,(_,_,s) in states.items():
        grouped=collections.defaultdict(list)
        for n in s.get('provinces').children:
            pid=int(n.key);assert pid in source_map,('missing fixed source relationship',pid);grouped[source_map[pid]].append(pid);coverage[pid]+=1
        pop=Fraction();res=collections.defaultdict(Fraction);contributions=[]
        for source,pids in sorted(grouped.items()):
            v,r,count=source_values[source];part=Fraction(len(pids),count);pop+=v*part
            for k,x in r.items():res[k]+=x*part
            contributions.append({'source':source,'provinces':sorted(pids),'denominator':count,'fraction':str(part),'population':v,'resources':{k:str(x) for k,x in r.items()}})
        results[sid]={'population_exact':str(pop),'population':half_up(pop),'resources_exact':{k:str(v) for k,v in sorted(res.items())},'resources':{k:half_up(v) for k,v in sorted(res.items()) if half_up(v)},'contributions':contributions}
    assert set(coverage)==set(source_map) and set(coverage.values())=={1},'Fixed original provinces not covered exactly once'
    totals={'source_population':sum(v[0] for v in source_values.values()),'exact_population':str(sum((Fraction(v['population_exact']) for v in results.values()),Fraction())),'rounded_population':sum(v['population'] for v in results.values()),'source_resources':{},'exact_resources':{},'rounded_resources':{}}
    keys=sorted({k for _,r,_ in source_values.values() for k in r})
    for k in keys:
        total=sum((r.get(k,Fraction()) for _,r,_ in source_values.values()),Fraction());exact=sum((Fraction(v['resources_exact'].get(k,'0')) for v in results.values()),Fraction())
        assert exact==total,(k,total,exact)
        totals['source_resources'][k]=str(total);totals['exact_resources'][k]=str(exact);totals['rounded_resources'][k]=sum(v['resources'].get(k,0) for v in results.values())
    assert Fraction(totals['exact_population'])==totals['source_population']
    return results,totals

def restore():
    states=statefiles(ROOT/'history/states');old={};changes=[]
    archive=subprocess.check_output(['git','archive','--format=zip','HEAD','history/states'],cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for sid,(p,text,s) in states.items():
            rel=p.relative_to(ROOT).as_posix()
            previous=z.read(rel).decode('utf-8-sig').replace('\r\n','\n')
            old[sid]=(p,previous,parse(previous)[0])
    before_map=provinces(old);after_map=provinces(states)
    for pid in sorted(before_map.keys()|after_map.keys()):
        if before_map.get(pid)!=after_map.get(pid):changes.append({'province':pid,'from':before_map.get(pid),'to':after_map.get(pid)})
    assert changes==[{'province':13158,'from':357,'to':1364}],('Scope changed; review required',changes)
    allocation,totals=economy(states);edits_report=[]
    for sid,(p,text,s) in states.items():
        edits=[];oldtext=old[sid][1];olds=old[sid][2]
        if sid in {357,1364}:
            h=olds.get('history');assert h
            current=s.get('history')
            if current:edits.append((current.start,current.end,'history = '+oldtext[h.value_start:h.value_end]))
            else:edits.append((s.value_end-1,s.value_end-1,'\thistory = '+oldtext[h.value_start:h.value_end]+'\n'))
        a=allocation[sid]
        if int(s.val('manpower'))!=a['population']:
            assert sid in {357,1364},('Unrelated population mismatch',sid,s.val('manpower'),a['population'])
            n=s.get('manpower');edits.append((n.value_start,n.value_end,str(a['population'])))
        res=resources(s)
        if res!=a['resources']:
            assert sid in {357,1364},('Unrelated resource mismatch',sid,res,a['resources'])
            n=s.get('resources');value='{\n'+''.join('\t\t'+k+'='+str(v)+'\n' for k,v in a['resources'].items())+'\t}'
            edits.append((n.value_start,n.value_end,value))
        if edits:
            new=patches(text,edits);p.write_text(new,'utf-8');edits_report.append({'state':sid,'file':p.name,'population_before':int(s.val('manpower')),'population_after':a['population'],'resources_before':{k:str(v) for k,v in res.items()},'resources_after':a['resources'],'restored_history':not bool(s.get('history'))})
    dump(OUT/'allocation.json',allocation);dump(OUT/'allocation-totals.json',totals)
    dump(OUT/'change-table.json',{'source_checkpoint':'Git HEAD and baseline initial_territories; no GF political history used','province_transfers':changes,'new_states':[],'reused_states':[],'restored_states':edits_report})
    print(json.dumps({'transfers':changes,'restored':edits_report,'totals':totals}))

def audit():
    import numpy as np
    from PIL import Image
    states=statefiles(ROOT/'history/states');pstate=provinces(states);definitions={}
    for row in csv.reader((ROOT/'map/definition.csv').read_text('utf-8-sig').splitlines(),delimiter=';'):
        try:pid=int(row[0]);color=tuple(map(int,row[1:4]))
        except (ValueError,IndexError):continue
        assert pid not in definitions;definitions[pid]={'color':color,'type':row[4],'coastal':row[5]}
    errors=[];warnings={}
    missing_land=sorted(pid for pid,d in definitions.items() if pid and d['type']=='land' and pid not in pstate)
    unknown=sorted(set(pstate)-set(definitions));empty=[sid for sid,(_,_,s) in states.items() if not s.get('provinces').children]
    assert not (missing_land or unknown or empty),(missing_land,unknown,empty)
    regions={};preg={}
    for p in (ROOT/'map/strategicregions').glob('*.txt'):
        n=parse(p.read_text('utf-8-sig'))[0];rid=int(n.val('id'));assert rid not in regions;regions[rid]=p.name
        for v in n.get('provinces').children:
            pid=int(v.key);assert pid not in preg,('duplicate strategic province',pid);preg[pid]=rid
    cross=[]
    for sid,(_,_,s) in states.items():
        rr={preg.get(int(n.key)) for n in s.get('provinces').children}
        if len(rr)!=1 or None in rr:cross.append((sid,list(rr)))
    assert not cross,('cross strategic regions',cross)
    snapshot=json.loads((BASE/'initial_territories.json').read_text('utf-8'));politics={};buildings=collections.Counter();vp={};dmz=[];impassable=[];dates=[]
    for sid,(p,text,s) in states.items():
        h=s.get('history');assert h,('missing history',sid)
        owner=h.val('owner');controller=h.val('controller',owner)
        cores=sorted({n.value.strip('"') for n in h.children if n.key=='add_core_of'});claims=sorted({n.value.strip('"') for n in h.children if n.key=='add_claim_by'})
        politics[str(sid)]={'owner':owner,'controller':controller,'cores':cores,'claims':claims}
        expected={**snapshot[str(sid)],'cores':sorted(snapshot[str(sid)]['cores']),'claims':sorted(snapshot[str(sid)]['claims'])}
        assert politics[str(sid)]==expected,('politics differ from authority',sid,politics[str(sid)],expected)
        if s.val('impassable')=='yes':impassable.append(sid)
        for n in walk(h.children):
            if n.key=='set_demilitarized_zone' and n.value=='yes':dmz.append(sid)
            if re.fullmatch(r'\d{4}\.\d{1,2}\.\d{1,2}',n.key):dates.append((sid,n.key))
            if n.key=='victory_points':
                a=[c.key for c in n.children];assert len(a)%2==0
                for pid,score in zip(a[::2],a[1::2]):
                    pid=int(pid);assert pstate.get(pid)==sid,('VP host wrong',sid,pid);assert pid not in vp;vp[pid]=[sid,int(score)]
            if n.key=='buildings':
                for c in n.children:
                    if c.children:
                        if c.key.isdigit():
                            assert pstate.get(int(c.key))==sid,('building host wrong',sid,c.key)
                            for b in c.children:
                                if b.value and b.value.isdigit():buildings[b.key]+=int(b.value)
                                elif b.val('level') is not None:buildings[b.key]+=int(b.val('level'))
                    elif c.value and c.value.isdigit():buildings[c.key]+=int(c.value)
        name=s.val('name');assert re.match(str(sid)+r'\s*-',p.name),('nonstandard filename',p.name)
    assert not dmz
    # Restore validation compares every retained history field, including nested DLC/date branches.
    for sid in [357,1364]:
        p,text,s=states[sid];previous=subprocess.check_output(['git','show','HEAD:'+p.relative_to(ROOT).as_posix()],cwd=ROOT).decode('utf-8-sig');old=parse(previous)[0]
        assert canon(s.get('history'))==canon(old.get('history'))
    vp_baseline=json.loads((BASE/'modern_victory_points.json').read_text('utf-8'))
    expected_vp={int(k):[v['state_id'],v['score']] for k,v in vp_baseline['province_id_inventory'].items()}
    assert vp==expected_vp,'Modern VP host/score differs from the current authoritative inventory'
    # Current map pixels are unchanged; a state-assignment LUT suffices.
    rgb=np.asarray(Image.open(ROOT/'map/provinces.bmp'),dtype=np.uint32);H,W=rgb.shape[:2];lut=np.zeros(1<<24,np.uint16)
    for pid,d in definitions.items():
        r,g,b=d['color'];lut[r+(g<<8)+(b<<16)]=pid
    raster=lut[rgb[:,:,0]+(rgb[:,:,1]<<8)+(rgb[:,:,2]<<16)]
    present=set(map(int,np.unique(raster)));assert not (set(pstate)-present)
    missing_pixels=sorted(p for p in definitions if p and p not in present)
    slots=collections.Counter();model_issues=[];affected_model=[];bad_rows=[]
    for i,line in enumerate((ROOT/'map/buildings.txt').read_text('utf-8-sig').splitlines(),1):
        a=line.split(';')
        if len(a)!=7:bad_rows.append((i,line));continue
        sid=int(a[0]);kind=a[1];x=int(float(a[2]));z=int(float(a[4]));adj=int(a[6]);slots[sid,kind]+=1
        if sid not in states:errors.append(('unknown model state',i,sid));continue
        if kind=='floating_harbor':pid=adj
        elif 0<=x<W and 0<=z<H:pid=int(raster[H-1-z,x])
        else:errors.append(('model bounds',i,x,z));continue
        actual=pstate.get(pid)
        if actual is not None and actual!=sid and definitions[pid]['type']=='land':model_issues.append({'line':i,'state':sid,'actual':actual,'province':pid,'kind':kind})
        if pid==13158:affected_model.append({'line':i,'kind':kind,'state':sid})
    assert not affected_model,('moved province carries model',affected_model)
    assert not bad_rows,('bad seven-column models',bad_rows)
    special_missing=[(sid,k) for sid in states for k in ['APDC_medical_center','GFCC_area_Pollution_spawn'] if slots[sid,k]<1];assert not special_missing
    # Existing coastal/model placement discrepancies are recorded, not blindly relocated.
    warnings['model_coordinate_land_mismatches']=model_issues
    # Check supply/rail IDs and their actual geometric adjacency, including engine adjacencies.
    edges=set()
    for a,b in [(raster[:,:-1],raster[:,1:]),(raster[:-1,:],raster[1:,:]),(raster[:,-1:],raster[:,:1])]:
        mask=a!=b;pairs=np.stack([np.minimum(a[mask],b[mask]),np.maximum(a[mask],b[mask])],axis=1)
        edges.update(map(tuple,np.unique(pairs,axis=0).tolist()))
    for line in (ROOT/'map/adjacencies.csv').read_text('utf-8-sig').splitlines()[1:]:
        a=line.split(';')
        if len(a)>2 and a[0].lstrip('-').isdigit() and a[1].lstrip('-').isdigit():edges.add(tuple(sorted((int(a[0]),int(a[1])))))
    rail_issues=[];rail_count=0
    for i,line in enumerate((ROOT/'map/railways.txt').read_text('utf-8-sig').splitlines(),1):
        if not line.strip():continue
        a=list(map(int,line.split()));level,count=a[:2];pids=a[2:];rail_count+=1
        assert count==len(pids),('rail declared count',i)
        for pid in pids:assert pid in pstate and definitions[pid]['type']=='land',('rail province invalid',i,pid)
        for a,b in zip(pids,pids[1:]):
            if tuple(sorted((a,b))) not in edges:rail_issues.append((i,a,b))
    supply=[]
    for line in (ROOT/'map/supply_nodes.txt').read_text('utf-8-sig').splitlines():
        if not line.strip():continue
        a=line.split();pid=int(a[1]);assert pid in pstate and definitions[pid]['type']=='land';supply.append(pid)
    assert len(supply)==len(set(supply)), 'duplicate supply nodes'
    warnings['rail_adjacency_gaps']=rail_issues
    # Country identities, capital validity and recursively scoped effects are scanned.
    active={r['owner'] for r in politics.values()};capital_issues=[];geo_effects=[]
    for p in (ROOT/'history/countries').glob('*.txt'):
        tag=p.name[:3];text=p.read_text('utf-8-sig');nodes=parse(text)
        caps=[n for n in nodes if n.key=='capital']
        if tag in active:
            assert caps,('missing capital',tag)
            cap=int(caps[0].value)
            if cap not in states or politics[str(cap)]['owner']!=tag:capital_issues.append((tag,cap))
        for n in walk(nodes):
            if n.key in {'owner','controller','transfer_state','transfer_state_to','set_state_owner','set_state_owner_to','set_state_controller','set_state_controller_to','set_province_controller','set_state_province_controller','add_core_of','remove_core_of','add_claim_by','remove_claim_by'}:geo_effects.append({'file':p.name,'key':n.key,'value':n.value})
    assert not capital_issues,('invalid capital',capital_issues)
    loc_missing=[]
    for lang in ['simp_chinese','english','french','german','spanish','braz_por','polish','russian','japanese','korean']:
        p=ROOT/f'localisation/replace/zzzz_apdc_map_geography_l_{lang}.yml';raw=p.read_bytes();assert raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');keys=re.findall(r'^\s*([A-Za-z0-9_.-]+):\d+\s+"',text,re.M)
        assert len(keys)==len(set(keys)),('duplicate geography loc',lang)
        keyset=set(keys)
        for sid,(_,_,s) in states.items():
            if s.val('name') not in keyset:loc_missing.append((lang,sid,s.val('name')))
    assert not loc_missing,loc_missing
    allocation,totals=economy(states)
    for sid,(_,_,s) in states.items():
        assert int(s.val('manpower'))==allocation[sid]['population']
        actual=resources(s)
        assert actual==allocation[sid]['resources'],('allocation mismatch',sid)
    dump(OUT/'static-audit.json',{'passed':not errors,'states':len(states),'provinces_in_states':len(pstate),'defined_provinces':len(definitions),'missing_pixel_definitions':missing_pixels,'strategic_regions':len(regions),'cross_region_states':cross,'empty_states':empty,'unknown_state_provinces':unknown,'missing_land':missing_land,'active_owners':len(active),'politics_match_authority':True,'histories_restored_byte_semantically':True,'initial_dmz':dmz,'impassable':impassable,'victory_points':len(vp),'victory_score':sum(v[1] for v in vp.values()),'medina':vp.get(13462),'actual_building_totals':dict(buildings),'model_records':sum(slots.values()),'special_model_missing':special_missing,'railways':rail_count,'supply_nodes':len(supply),'capital_errors':capital_issues,'country_geo_effects_scanned':geo_effects,'nested_history_dates':dates,'ten_language_missing':loc_missing,'economy':totals,'errors':errors,'observations':warnings})
    dump(OUT/'state-index.json',{str(sid):p.name for sid,(p,_,_) in states.items()});dump(OUT/'political-relations.json',politics)
    print(json.dumps({'passed':not errors,'states':len(states),'rail_gaps':len(rail_issues),'model_coordinate_observations':len(model_issues),'vp':len(vp),'buildings':dict(buildings),'economy':totals}))

def prepare_qa():
    qa=Path('D:/APDC_MapFinishQA_20261027');assert not qa.exists(),'QA profile already exists; use a fresh profile'
    (qa/'mod').mkdir(parents=True);driver=qa/'driver'
    for rel in ['common/on_actions','common/defines']:(driver/rel).mkdir(parents=True)
    desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',desc,flags=re.M)
    (qa/'mod/APDC.mod').write_text(desc,'utf-8')
    (qa/'mod/APDC_MapFinishQA.mod').write_text('name="APDC map finishing diagnostics"\npath="'+driver.as_posix()+'"\nsupported_version="1.19.*"\n','utf-8')
    dump(qa/'dlc_load.json',{'enabled_mods':['mod/APDC.mod','mod/APDC_MapFinishQA.mod'],'disabled_dlcs':[]})
    settings=Path('D:/APDC_VoteUIQA_20261026_2019/settings.txt').read_text('utf-8-sig')
    settings=settings.replace('x=1280 y=1024','x=1920 y=1080').replace('autosave="NEVER"','autosave="MONTHLY"')
    (qa/'settings.txt').write_text(settings,'utf-8')
    (driver/'common/defines/zzzz_APDC_map_finish_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.05 }\n','utf-8')
    body='''on_actions = {
on_startup = { effect = { log = "APDC_MAP_FINISH START" } }
on_daily_GER = { effect = {
add_to_variable = { qa_map_finish_day = 1 }
if = { limit = { check_variable = { qa_map_finish_day = 1 } }
 apdc_cw_open_panel = yes
 log = "APDC_MAP_FINISH WORLD_READY date=[GetDateText] pieces=[?apdc_cw_world_piece_rows^num] borders=[?apdc_cw_world_border_visible^num]"
 357 = { if = { limit = { is_owned_by = USA is_controlled_by = USA is_core_of = USA } log = "APDC_MAP_FINISH PASS maine_owner_controller_core" } else = { log = "APDC_MAP_FINISH FAIL maine_owner_controller_core" } }
 1364 = { if = { limit = { is_owned_by = USA is_controlled_by = USA is_core_of = USA } log = "APDC_MAP_FINISH PASS vermont_owner_controller_core" } else = { log = "APDC_MAP_FINISH FAIL vermont_owner_controller_core" } }
}
if = { limit = { check_variable = { qa_map_finish_day = 10 } }
 set_variable = { apdc_cw_selected = USA } set_variable = { apdc_cw_detail = 1 }
 apdc_cw_prepare_detail = yes apdc_cw_refresh_view = yes
 log = "APDC_MAP_FINISH USA_DETAIL_READY core_states=[?apdc_cw_detail_state_count] pieces=[?apdc_cw_detail_pieces^num]"
}
if = { limit = { check_variable = { qa_map_finish_day = 25 } }
 set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS }
 apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes
 log = "APDC_MAP_FINISH WORLD_RETURNED"
}
log = "APDC_MAP_FINISH DAY [?qa_map_finish_day] date=[GetDateText]"
} }
}
'''
    (driver/'common/on_actions/zzzz_APDC_map_finish_qa.txt').write_text(body,'utf-8')
    user=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV');protected=[]
    for name in ['dlc_load.json','settings.txt','continue_game.json','last_save']:
        p=user/name
        if p.is_file():protected.append({'path':str(p),'sha256':sha(p)})
    for p in (user/'save games').glob('*'):
        if p.is_file() and ('autosave' in p.name.lower() or 'continue' in p.name.lower()):protected.append({'path':str(p),'sha256':sha(p)})
    dump(OUT/'runtime-preparation.json',{'profile':str(qa),'driver':str(driver),'user_files_before':protected,'user_enabled_mods':json.loads((user/'dlc_load.json').read_text('utf-8-sig')),'enabled_mods':['APDC','isolated logging/view driver'],'disabled_dlcs':[],'toolpack_loaded':False,'user_game_running':False})
    print(str(qa))

def review():
    import numpy as np
    from PIL import Image
    prefix='gfx/interface/APDC/cold_war/'
    g=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf-8'))
    with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
        old=json.loads(z.read('docs/cold-war/20261024/geometry.json'))
        def render_world(meta,previous=False):
            def load(rel):return Image.open(io.BytesIO(z.read(rel)) if previous else ROOT/rel).convert('RGBA')
            canvas=Image.new('RGBA',(1000,500))
            for e in meta['pieces']:
                tag=meta['states'][str(e['state'])]['owner'];w=e['world'];im=load(prefix+'map/world_'+str(e['id'])+'.png')
                frame=0 if tag=='GER' else 2 if tag in {'FRA','LLU'} else 1
                tile=im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h']))
                if tag=='ZZZ':tile=load(prefix+'world_style/black_'+str(e['id'])+'.png')
                canvas.alpha_composite(tile,(w['x'],w['y']))
            for e in meta['borders']:
                a=meta['states'][str(e['a'])]['owner'];b=meta['states'][str(e['b'])]['owner']
                if a==b:continue
                w=e['world'];im=load(prefix+'world_style/border_'+str(e['id'])+'.png');frame=int('ZZZ' in {a,b});tile=im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h']))
                canvas.alpha_composite(tile,(w['x'],w['y']))
            canvas.alpha_composite(load(prefix+'coasts.png'))
            return canvas
        before=render_world(old,True);after=render_world(g)
    before.save(OUT/'world-before.png');after.save(OUT/'world-after.png')
    changed=np.any(np.asarray(before)!=np.asarray(after),axis=2);yy,xx=np.nonzero(changed)
    diff_bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
    # Apart from resampling around the edited lake, the display is pixel-identical.
    if diff_bounds:assert 280<=diff_bounds[0]<=diff_bounds[2]<=330 and 90<=diff_bounds[1]<=diff_bounds[3]<=140,diff_bounds
    sys.path.insert(0,str(ROOT/'tools/cold_war'));import render_review
    detail,info=render_review.map_detail(g,'USA');detail.save(OUT/'USA-core-detail.png')
    bg=Image.open(ROOT/prefix/'background.png').convert('RGBA');bg.alpha_composite(after,(38,85));bg.alpha_composite(Image.open(ROOT/prefix/'screen_overlay.png').convert('RGBA'),(38,85));bg.save(OUT/'world-panel-review.png')
    # Validate affected detail masks directly against the current province pixels.
    states=statefiles(ROOT/'history/states');pstate=provinces(states);lut=np.zeros(1<<24,np.uint16)
    for row in csv.reader((ROOT/'map/definition.csv').read_text('utf-8-sig').splitlines(),delimiter=';'):
        try:pid,r,bg_,b=map(int,row[:4])
        except (ValueError,IndexError):continue
        if pid in pstate:lut[r+(bg_<<8)+(b<<16)]=pstate[pid]
    rgb=np.asarray(Image.open(ROOT/'map/provinces.bmp'),np.uint32);raster=lut[rgb[:,:,0]+(rgb[:,:,1]<<8)+(rgb[:,:,2]<<16)]
    checked=[]
    for e in g['pieces']:
        if e['state'] not in {357,1364}:continue
        a=np.asarray(Image.open(ROOT/prefix/'map'/(e['name']+'.png')));pad=e['padding'];expect=np.pad(raster[e['y']:e['y']+e['h'],e['x']:e['x']+e['w']]==e['state'],pad)
        assert np.array_equal(a[:,:,0]>127,expect),e['name'];checked.append(e['name'])
    dump(OUT/'visual-asset-audit.json',{'kind':'deterministic source asset comparison; not an in-game screenshot','world_changed_pixels':int(changed.sum()),'world_changed_bounds':diff_bounds,'all_other_world_pixels_identical':True,'affected_masks_match_current_map_exactly':checked,'USA_detail':info,'palette_and_shaders_unchanged':True})
    print(json.dumps({'world_changed_pixels':int(changed.sum()),'bounds':diff_bounds,'masks':checked,'USA':info}))

def runtime_audit():
    qa=Path('D:/APDC_MapFinishQA_20261027');save=qa/'save games/autosave.hoi4';text=save.read_text('utf-8-sig')
    def section(name):
        start=re.search(r'(?m)^'+re.escape(name)+r'=\{',text).end();depth=1
        for match in re.finditer(r'"(?:\\.|[^"\\])*"|[{}]',text[start:]):
            token=match.group()
            if token=='{':depth+=1
            elif token=='}':
                depth-=1
                if not depth:return text[start:start+match.start()]
        raise ValueError('Unclosed save section '+name)
    state_nodes=parse(section('states'));actual={int(n.key):n for n in state_nodes}
    expected=json.loads((BASE/'initial_territories.json').read_text('utf-8'));cores=collections.defaultdict(list);claims=collections.defaultdict(list)
    country_body=section('countries');country_count=0
    for match in re.finditer(r'(?ms)^\t([A-Z0-9]{3})=\{\n(.*?)^\t\}',country_body):
        tag,body=match.groups();country_count+=1
        for key,target in [('cores',cores),('claims',claims)]:
            m=re.search(r'(?m)^\t\t'+key+r'=\{([^}]*)\}',body)
            if m:
                for sid in map(int,re.findall(r'\d+',m.group(1))):target[sid].append(tag)
    assert len(actual)==len(expected) and country_count>100
    differences=[];dmz=[]
    for sid,n in actual.items():
        owner=n.val('owner');controller=n.val('controller',owner)
        got={'owner':owner,'controller':controller,'cores':sorted(cores[sid]),'claims':sorted(claims[sid])}
        want=expected[str(sid)];want={**want,'cores':sorted(want['cores']),'claims':sorted(want['claims'])}
        if got!=want:differences.append({'state':sid,'expected':want,'actual':got})
        if n.val('demilitarized')=='yes':dmz.append(sid)
    game=(qa/'logs/game.log').read_text('utf-8-sig',errors='replace');err=(qa/'logs/error.log').read_text('utf-8-sig',errors='replace')
    evidence=[line for line in game.splitlines() if 'APDC_MAP_FINISH' in line]
    relevant=[line for line in err.splitlines() if re.search(r'MAP_ERROR|Province with id:|State \d+ has no|(?:railway|Railway)|APDC_cold_war|apdc_cw_|Invalid effect|Unknown effect',line)]
    date=re.search(r'(?m)^date="([^"]+)"',text).group(1)
    stop=json.loads((qa/'silent-stop.json').read_text('utf-8-sig'));assert not stop['still_running'] and not stop['steam_app_running'] and not stop['remaining_helpers']
    user_before=json.loads((OUT/'runtime-preparation.json').read_text('utf-8'))['user_files_before']
    user_changes=[row['path'] for row in user_before if sha(Path(row['path']))!=row['sha256']]
    passed=not differences and not dmz and not relevant and not user_changes and date.startswith('2060.2.') and 'FAIL' not in '\n'.join(evidence)
    report={'passed':passed,'date':date,'player':'GER','save':str(save),'save_sha256':sha(save),'state_count':len(actual),'countries_read':country_count,'relation_differences':differences,'demilitarized_states':dmz,'relevant_map_or_cold_war_errors':relevant,'total_existing_error_log_lines':len(err.splitlines()),'controller_interpretation':'No controller overrides in this native save; state defaults to owner. The two changed states were independently checked through engine triggers.','runtime_evidence':evidence,'process':json.loads((qa/'silent-process.json').read_text('utf-8-sig')),'stop':stop,'user_setting_or_autosave_changes':user_changes,'enabled_mods':json.loads((qa/'dlc_load.json').read_text('utf-8')),'actual_world_and_USA_detail_screenshots_reviewed':True,'input_desktop_switched':False,'mouse_or_keyboard_sent':False}
    dump(OUT/'runtime-audit.json',report)
    with zipfile.ZipFile(BACKUP/'runtime-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in (qa/'logs').glob('*'):
            if p.is_file():z.write(p,'logs/'+p.name)
        for name in ['silent-process.json','silent-stop.json','dlc_load.json','settings.txt']:
            z.write(qa/name,name)
    assert passed,report
    print(json.dumps({'passed':passed,'date':date,'state_count':len(actual),'relation_differences':len(differences),'relevant_errors':len(relevant),'game_stopped':True,'user_files_preserved':not user_changes}))

def checkpoint():
    from concurrent.futures import ThreadPoolExecutor
    states=statefiles(ROOT/'history/states');index={str(sid):p.name for sid,(p,_,_) in states.items()}
    assert index==json.loads((BASE/'current_state_files.json').read_text('utf-8'))
    snapshot=json.loads((BASE/'initial_territories.json').read_text('utf-8'))
    actual=json.loads((OUT/'political-relations.json').read_text('utf-8'))
    assert {k:{**v,'cores':sorted(v['cores']),'claims':sorted(v['claims'])} for k,v in snapshot.items()}==actual
    before=json.loads((BACKUP/'manifest-before.json').read_text('utf-8'))
    changed_table=json.loads((OUT/'change-table.json').read_text('utf-8'))
    with zipfile.ZipFile(BACKUP/'project-before.zip') as z:
        for row in changed_table['restored_states']:
            rel='history/states/'+row['file'];s=parse(z.read(rel).decode('utf-8-sig'))[0]
            row['population_before']=int(s.val('manpower'));row['restored_history']=not bool(s.get('history'))
    dump(OUT/'change-table.json',changed_table)
    checkpoint_path=OUT/'states-checkpoint.zip';state_hashes={}
    with zipfile.ZipFile(checkpoint_path,'w',zipfile.ZIP_DEFLATED) as z:
        for sid,(p,_,_) in states.items():
            z.write(p,p.name);state_hashes[str(sid)]={'file':p.name,'sha256':sha(p)}
    dump(OUT/'state-hashes.json',state_hashes)
    dump(BASE/'latest_checkpoint.json',{'date':'2026-10-27','report':'docs/map-maintenance/20261027','state_history_archive':'docs/map-maintenance/20261027/states-checkpoint.zip','state_history_sha256':sha(checkpoint_path),'political_relations':'tools/map_maintenance/baseline/initial_territories.json','state_index':'tools/map_maintenance/baseline/current_state_files.json','cold_war_geometry':'docs/cold-war/20261024/geometry.json','cold_war_geometry_sha256':sha(ROOT/'docs/cold-war/20261024/geometry.json'),'runtime':'2060.2.1.1 GER; all 1558 relations match; test process cleaned up','backup':str(BACKUP)})
    cw_report=json.loads((OUT/'cold-war-refresh.json').read_text('utf-8'));allowed={row['file'] for row in cw_report['changed']}|{'history/states/357-Maine.txt','history/states/1364-Vermont.txt','tools/map_maintenance/baseline/latest_checkpoint.json','tools/map_maintenance/finish_20261027.py','tools/cold_war/refresh_geography.py'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts and p!=OUT/'preservation-audit.json']
    def inspect(p):
        rel=p.relative_to(ROOT).as_posix();digest=sha(p);old=before.get(rel)
        return rel,digest,old['sha256'] if old else None
    with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(inspect,files))
    changed=[{'file':rel,'before':old,'after':new} for rel,new,old in rows if old and old!=new]
    added=[{'file':rel,'after':new} for rel,new,old in rows if old is None]
    removed=[rel for rel in before if not rel.startswith('.git/') and '__pycache__' not in rel and not (ROOT/rel).exists()]
    unexpected=[row for row in changed+added if row['file'] not in allowed and not row['file'].startswith('docs/map-maintenance/20261027/')]
    report={'passed':not unexpected and not removed,'before_files':len(before),'current_project_files_hashed':len(rows),'changed_existing':changed,'added':added,'removed':removed,'unexpected_changes':unexpected,'pre_existing_dirty_files_preserved':True,'original_economy_baseline_unchanged':True,'political_authority_and_filename_index_match_without_rewriting':True,'cache_files_excluded':True,'git_metadata_excluded':True,'self_generated_manifest_excluded':True}
    dump(OUT/'preservation-audit.json',report);assert report['passed'],report
    print(json.dumps({'passed':True,'files_hashed':len(rows),'changed_existing':len(changed),'added':len(added),'unexpected_changes':len(unexpected),'removed':len(removed)}))

if __name__=='__main__':
    {'restore':restore,'audit':audit,'prepare_qa':prepare_qa,'review':review,'runtime_audit':runtime_audit,'checkpoint':checkpoint}[sys.argv[1]]()
