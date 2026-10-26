"""Native world-only colour check, including ownership changes and an unchanged detail."""
import sys,json
from common import ROOT,metadata,parse,block
import qa

def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)

def prepare():
    sys.argv.append('--world-review');profile=qa.prepare();driver=profile/'driver';g=metadata();source=(ROOT/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8');nodes=list(walk(parse(source)))
    def callback(key):
        node=next(n for n in nodes if n.key==key);return source[node.value_start+1:node.value_end-1]+'\n'
    wilderness={int(sid) for sid,s in g['states'].items() if s['owner']=='ZZZ'}
    border=next(e for e in g['borders'] if (e['a'] in wilderness)!=(e['b'] in wilderness));sid=border['a'] if border['a'] in wilderness else border['b']
    piece=next(e for e in g['pieces'] if e['state']==sid)
    french=next(e for e in g['pieces'] if g['states'][str(e['state'])]['owner']=='FRA')
    body='add_to_variable = { apdc_cw_visibility_day = 1 }\n'
    stages=[('FIRST_OPEN',callback('apdc_cw_entry_button_click')),('DETAIL',callback(f'apdc_cw_world_{french["id"]}_click')),('RETURN',callback('apdc_cw_return_click')),('TRANSFER',f'{sid} = {{ transfer_state_to = GER }}\n'),('RESTORE',f'{sid} = {{ transfer_state_to = ZZZ }}\n')]
    for i,(label,action) in enumerate(stages):
        day=1+i*7
        trace=f'log = "APDC_CW_VISIBILITY STAGE {label} day=[?apdc_cw_visibility_day] owner=[?apdc_cw_world_piece_owners^{piece["id"]}.GetTag] fill=[?apdc_cw_world_fill_images^{piece["id"]}.GetTokenKey] edge=[?apdc_cw_world_border_frames^{border["id"]}]"\n'
        body+=block('if',f'limit = {{ check_variable = {{ apdc_cw_visibility_day = {day} }} }}\n'+action+trace)
    body+=block('if','limit = { check_variable = { apdc_cw_visibility_day = 36 } }\nclr_country_flag = apdc_cw_open\napdc_cw_run_qa = yes')
    body+=block('if','limit = { check_variable = { apdc_cw_visibility_day = 37 } }\nset_variable = { qa_batch_difference = global.apdc_cw_daily_batches }\nsubtract_from_variable = { qa_batch_difference = qa_batches_before }\nif = { limit = { check_variable = { qa_batch_difference = 1 } } log = "APDC_CW_QA PASS global_daily_batch_runs_once" } else = { log = "APDC_CW_QA FAIL global_daily_batch_runs_once" }')
    body+='log = "APDC_CW_VISIBILITY DAY [?apdc_cw_visibility_day] [GetDateText]"\n'
    (driver/'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('on_actions = { on_daily_GER = { effect = { '+body+' } } }','utf-8')
    out=ROOT/'docs/cold-war/20261025-uninhabited-colors';(out/'profile.txt').write_text(str(profile),'utf-8');(out/'test-target.json').write_text(json.dumps({'state':sid,'piece':piece['id'],'border':border['id'],'stages':[s for s,a in stages]},indent=2),'utf-8')
    print(json.dumps({'profile':str(profile),'state':sid,'stages':[s for s,a in stages]}));return profile

if __name__=='__main__':prepare()
