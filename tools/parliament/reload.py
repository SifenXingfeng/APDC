"""Prepare or verify a real save reload, using the same isolated QA profile."""
import argparse
import re
from common import *
from audit import PROFILE, save_country
from runtime import assertion


def prepare():
    path=PROFILE/'save games/autosave.hoi4';raw=path.read_bytes();save=raw.decode('utf-8-sig')
    ger=save_country(save,'GER');variables=ger.get('variables')
    snapshot={n.key:float(n.value) for n in variables.children if n.key.startswith(P) and n.value is not None and re.fullmatch(r'-?[\d.]+',n.value)}
    assert snapshot[P+'agenda']==1 and snapshot[P+'bill_work']>0,'Need an in-progress saved bill'
    original_date=re.search(r'^date="([^"]+)"',save,re.M).group(1)
    saved={'date':original_date,'sha256':hashlib.sha256(raw).hexdigest(),'fields':snapshot}
    (REPORT/'reload-before.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    backup=Path(json.loads(read('docs/parliament/20261107-implementation/backup.json'))['backup'])/'runtime-accepted'
    backup.mkdir(exist_ok=True)
    (backup/'before-reload.hoi4').write_bytes(raw)
    stable=['term','election_serial','free_prime','free_deputy','bill_kind','bill_target','bill_option','bill_base_days','role_7','role_8']
    stable += ['seats_'+p for p in PARTIES]+['seat_colors^'+str(i) for i in range(500)]
    test=' '.join(ck(k,'=',snapshot.get(P+k,0)) for k in stable)
    work=snapshot[P+'bill_work']
    body=assertion(test,'reload_retains_seats_colors_term_offices_and_agenda')
    body+=assertion(ck('bill_work','>=',work)+' '+ck('bill_work','<',work+3),'reload_continues_saved_work')
    # Nonzero source and bill attitudes must also survive a genuine change
    # of government; this assertion is deliberately stronger than copying 0.
    body+='apdc_parl_set_liberalism_attitude_source = { NAME = apdc_parl_source_agreement VALUE = 4 }\napdc_parl_change_liberalism_bill_attitude = { VALUE = 7 }\n'
    body+=sv('qa_reload_work',var('bill_work'))+'apdc_parl_force_election = yes\n'
    body+=assertion(ck('bill_attitude_liberalism','=',7)+' '+ck('source_tip_liberalism_3','=',4)+' '+ck('bill_work','=',var('qa_reload_work'))+' '+ck('agenda','=',1),'nonzero_attitudes_and_work_survive_turnover')
    body+='set_country_flag = apdc_parl_qa_reload_checked\nlog = "APDC_PARL_QA VISUAL main"\n'
    day=op('qa_reload_day','add',1)+iff('NOT = { has_country_flag = apdc_parl_qa_reload_checked }',body)
    day+=iff(ck('qa_reload_day','=',3),'apdc_parl_select_role = { ROLE = 1 }\nlog = "APDC_PARL_QA VISUAL cabinet"\n')
    day+=iff(ck('qa_reload_day','=',7),'clr_country_flag = apdc_parl_candidate_panel_open\n'+sv('selected_group',5)+'apdc_parl_refresh_law_options = yes\nlog = "APDC_PARL_QA VISUAL law_side"\n')
    day+=iff(ck('qa_reload_day','=',11),'clear_variable = apdc_parl_selected_group\nlog = "APDC_PARL_QA VISUAL main_return"\n')
    day+=iff(ck('qa_reload_day','=',14),'log = "APDC_PARL_QA RELOAD_COMPLETE [GetDateText] work=[?apdc_parl_bill_work]"\n')
    action='on_daily_GER = { effect = { '+day+' } }'
    dest=PROFILE/'driver/common/on_actions/zzzzzz_apdc_parliament_qa.txt'
    dest.write_text(lower_parameters(block('on_actions',action)),encoding='utf-8')
    print(json.dumps({'prepared_reload':True,'saved_date':original_date,'saved_work':work},ensure_ascii=False))


def verify():
    game=(PROFILE/'logs/game.log').read_text('utf-8-sig',errors='replace')
    error=(PROFILE/'logs/error.log').read_text('utf-8-sig',errors='replace')
    failed=re.findall(r'APDC_PARL_QA FAIL (\w+)',game)
    passed=re.findall(r'APDC_PARL_QA PASS (\w+)',game)
    assert not failed,failed
    assert len(passed)==3 and 'APDC_PARL_QA RELOAD_COMPLETE' in game,passed
    relevant=[l for l in error.splitlines() if re.search(r'parliament|apdc_parl|APDC_cabinet|APDC_economic_system',l,re.I)]
    assert not relevant,relevant[:5]
    report={'status':'passed','checks':passed,'before':json.loads((REPORT/'reload-before.json').read_text('utf-8'))['date'],'completion':[l for l in game.splitlines() if 'RELOAD_COMPLETE' in l],'related_engine_errors':relevant,'actual_saved_game_loaded':True}
    (REPORT/'reload-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    folder=REPORT/'runtime/reload';folder.mkdir(exist_ok=True)
    for name in ['game.log','error.log','system.log']:(folder/name).write_bytes((PROFILE/'logs'/name).read_bytes())
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');args=ap.parse_args()
    verify() if args.verify else prepare()
