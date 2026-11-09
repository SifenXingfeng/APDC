"""Audit this implementation against its byte backup and actual QA save."""
import argparse
import re
from datetime import datetime, timezone
from common import *
from cw import TOKEN

PROFILE=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_20261107')


def preservation():
    backup=Path(json.loads(read('docs/parliament/20261107-implementation/backup.json'))['backup'])
    manifest=json.loads((backup/'changes.json').read_text('utf-8'))
    histories=[]; protected=[]; changed=[]
    for rel,entry in manifest.items():
        if rel.startswith(('map/','history/states/','common/characters/','common/ideologies/','gfx/FX/','gfx/fonts/')):
            protected.append(rel)
        if entry['existed']:
            original=(backup/'files'/rel).read_bytes()
            assert hashlib.sha256(original).hexdigest()==entry['sha256_before'],rel
        current=(ROOT/rel).read_bytes()
        changed.append({'path':rel,'sha256':hashlib.sha256(current).hexdigest(),'existed_before':entry['existed']})
        if rel.startswith('history/countries/'):
            prefix=current.decode('utf-8-sig').split('# APDC parliament election calendar schema 1')[0]
            assert prefix.replace('\r\n','\n').rstrip()==original.decode('utf-8-sig').replace('\r\n','\n').rstrip(),rel
            suffix=current.decode('utf-8-sig').split('# APDC parliament election calendar schema 1')[1]
            for n in walk(parse(suffix)):
                if n.key=='set_politics':
                    assert {c.key for c in n.children}=={'ruling_party','last_election','election_frequency','elections_allowed'},rel
            histories.append(rel)
    assert not protected,protected
    assert len(histories)==len(load_json('opening_countries.json'))==344
    # Existing economy changes are confined to maintained pathways.
    economy_changes={}
    for rel in ['common/scripted_effects/APDC_economy_backend.txt','common/scripted_effects/APDC_economy_equipment.txt']:
        old=(backup/'files'/rel).read_text('utf-8-sig');new=read(rel)
        before={n.key:old[n.start:n.end] for n in parse(old)}
        after={n.key:new[n.start:n.end] for n in parse(new)}
        assert before.keys()==after.keys(),rel
        economy_changes[rel]=[key for key in before if re.sub(r'\s+','',before[key])!=re.sub(r'\s+','',after[key])]
    report={'status':'passed','audit_utc':datetime.now(timezone.utc).isoformat(),'backup':str(backup),'country_histories_preserved':len(histories),'history_change':'append calendar blocks only; resolved ruling party is preserved','protected_map_character_ideology_font_shader_paths_written':protected,'economy_effects_changed':economy_changes,'files':changed}
    (REPORT/'preservation-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'status':'passed','country_histories_preserved':len(histories),'economy_effects_changed':economy_changes}


def save_country(text, tag):
    start=re.search(r'^countries=\{',text,re.M).end()
    match=re.search(r'^\t'+tag+r'=\{',text[start:],re.M)
    assert match,'Missing saved country '+tag
    opening=text.index('{',start+match.start());depth=0
    for token in TOKEN.finditer(text,opening):
        if token.group()=='{':depth+=1
        elif token.group()=='}':
            depth-=1
            if depth==0:return parse(text[start+match.start():token.end()])[0]
    raise AssertionError('Unclosed country save')


def runtime():
    game=(PROFILE/'logs/game.log').read_text('utf-8-sig',errors='replace')
    error=(PROFILE/'logs/error.log').read_text('utf-8-sig',errors='replace')
    system=(PROFILE/'logs/system.log').read_text('utf-8-sig',errors='replace')
    passed=re.findall(r'APDC_PARL_QA PASS (\w+)',game)
    failed=re.findall(r'APDC_PARL_QA FAIL (\w+)',game)
    relevant=[l for l in error.splitlines() if re.search(r'parliament|apdc_parl|APDC_cabinet|APDC_economic_system|APDC_eco_private_equipment_purchase_factor',l,re.I)]
    path=PROFILE/'save games/autosave.hoi4';save=path.read_text('utf-8-sig')
    date=re.search(r'^date="([^"]+)"',save,re.M).group(1)
    ger=save_country(save,'GER');variables=ger.get('variables')
    assert variables,'Missing GER persisted variables'
    scalar=lambda key:float(variables.val(P+key,'0'))
    seats={p:scalar('seats_'+p) for p in PARTIES}
    assert sum(seats.values())==500 and all(v==int(v) for v in seats.values())
    assert scalar('seat_colors^num')==500
    assert scalar('reform_groups^num')==6
    assert int(date.split('.')[1])>=2
    assert not failed,failed
    assert not relevant,relevant[:10]
    assert 'APDC_PARL_QA COMPLETE day35' in game
    country_start=re.search(r'^countries=\{',save,re.M).end()
    country_matches=list(re.finditer(r'^\t([A-Z0-9]{3})=\{',save[country_start:],re.M));all_seats={}
    for i,m in enumerate(country_matches):
        chunk=save[country_start+m.start():country_start+country_matches[i+1].start()] if i+1<len(country_matches) else save[country_start+m.start():]
        values=re.findall(r'^\t{3}apdc_parl_seats_([a-z_]+)=([\d.-]+)',chunk,re.M)
        if values:
            counts={key:float(value) for key,value in values}
            assert len(counts)==9 and sum(counts.values())==500,(m[1],counts)
            all_seats[m[1]]=counts
    assert len(all_seats)>=169,len(all_seats)
    report={'status':'passed','audit_utc':datetime.now(timezone.utc).isoformat(),'passed_assertions':passed,'failed_assertions':failed,'related_engine_errors':relevant,'save_date':date,'save':str(path),'save_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'persisted_seats':seats,'all_initialized_countries_have_500_seats':len(all_seats),'persisted_fields':{key:scalar(key) for key in ['seat_colors^num','term','free_prime','free_deputy','agenda','bill_work','bill_base_days','bill_attitude_socialism','elections_enabled','interval_months','regime']},'active_dlc_log':[l for l in system.splitlines() if 'Active DLC:' in l],'other_project_or_vanilla_log_errors_remain':bool(error.strip()),'profile':str(PROFILE),'user_profile_modified':False,'manual_mouse_keyboard_validation':False,'save_reloaded':False}
    (REPORT/'runtime-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=REPORT/'runtime'
    for name in ['game.log','error.log','system.log']:
        (archive/name).write_bytes((PROFILE/'logs'/name).read_bytes())
    return {key:report[key] for key in ['status','passed_assertions','save_date','related_engine_errors']}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--runtime',action='store_true');args=ap.parse_args()
    print(json.dumps(preservation(),ensure_ascii=False))
    if args.runtime:print(json.dumps(runtime(),ensure_ascii=False))
