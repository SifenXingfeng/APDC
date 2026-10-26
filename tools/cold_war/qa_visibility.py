"""Minimal first-open regression: no territory/control mutations before display."""
import sys,json,datetime
from pathlib import Path
from common import ROOT,parse,block,setv

def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)

def prepare(label):
    if label=='after':return prepare_scenes()
    sys.path.insert(0,str(ROOT/'tools/performance'))
    import prepare_runtime
    profile=Path('D:/APDC_CWVisibility_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    prepare_runtime.QA=profile;prepare_runtime.prepare(toolpack=True)
    settings=profile/'settings.txt';settings.write_text(settings.read_text('utf-8').replace('1280','1920').replace('720','1080'),'utf-8')
    source=(ROOT/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8')
    callback=next(node for node in walk(parse(source)) if node.key=='apdc_cw_entry_button_click')
    click=source[callback.value_start+1:callback.value_end-1]
    body='log = "APDC_CW_VISIBILITY BEFORE cache=[?apdc_cw_world_cache_version] ui=[?apdc_cw_map_ui_revision] GER=[?apdc_cw_world_frames^64] FRA=[?apdc_cw_world_frames^28]"\n'+click+'\n'
    body+='log = "APDC_CW_VISIBILITY OPEN ui=[?apdc_cw_map_ui_revision] GER=[?apdc_cw_world_frames^64] FRA=[?apdc_cw_world_frames^28]"\n'
    driver=profile/'driver';(driver/'common/scripted_effects').mkdir(exist_ok=True)
    (driver/'common/scripted_effects/APDC_cw_visibility.txt').write_text(block('apdc_cw_visibility_open',body),'utf-8')
    (driver/'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('on_actions = { on_daily_GER = { effect = { if = { limit = { NOT = { has_country_flag = apdc_cw_visibility_started } } set_country_flag = apdc_cw_visibility_started apdc_cw_visibility_open = yes } log = "APDC_CW_VISIBILITY DAY [GetDateText]" } } }','utf-8')
    out=ROOT/'docs/cold-war/20261025-map-display-regression';out.mkdir(parents=True,exist_ok=True);(out/(label+'-profile.txt')).write_text(str(profile),'utf-8')
    print(json.dumps({'profile':str(profile),'label':label,'before_open_mutations':'none; actual entry callback only'}))
    return profile

def prepare_scenes():
    import qa
    sys.argv.append('--world-review');profile=qa.prepare();driver=profile/'driver'
    source=(ROOT/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8');nodes=list(walk(parse(source)))
    def effect(key):
        node=next(node for node in nodes if node.key==key)
        return source[node.value_start+1:node.value_end-1]+'\n'
    enter=effect('apdc_cw_entry_button_click');close=effect('apdc_cw_close_click');detail=effect('apdc_cw_world_27_click');back=effect('apdc_cw_return_click')
    # Select an actual French-owned piece without changing any territory/data.
    from common import metadata
    geometry=metadata();entry=next(e for e in geometry['pieces'] if geometry['states'][str(e['state'])]['owner']=='FRA')
    detail=effect('apdc_cw_world_'+str(entry['id'])+'_click')
    stages=[('FIRST_OPEN',enter),('CLOSED',close),('REOPEN',enter),('DETAIL',detail),('RETURN',back)]
    body='add_to_variable = { apdc_cw_visibility_day = 1 }\n'
    for index,(label,action) in enumerate(stages):
        day=1+index*8
        marker=f'log = "APDC_CW_VISIBILITY STAGE {label} day=[?apdc_cw_visibility_day] ui=[?apdc_cw_map_ui_revision] builds=[?apdc_cw_world_cache_builds] FRA=[?apdc_cw_world_frames^28]"\n'
        body+=block('if','limit = { check_variable = { apdc_cw_visibility_day = '+str(day)+' } }\n'+action+marker)
    # Only after pristine first-open/close/reopen/detail/return captures run the
    # older integration suite that deliberately changes territory and control.
    body+=block('if','limit = { check_variable = { apdc_cw_visibility_day = 41 } }\nclr_country_flag = apdc_cw_open\napdc_cw_run_qa = yes')
    body+=block('if','limit = { check_variable = { apdc_cw_visibility_day = 42 } }\nset_variable = { qa_batch_difference = global.apdc_cw_daily_batches }\nsubtract_from_variable = { qa_batch_difference = qa_batches_before }\nif = { limit = { check_variable = { qa_batch_difference = 1 } } log = "APDC_CW_QA PASS global_daily_batch_runs_once" } else = { log = "APDC_CW_QA FAIL global_daily_batch_runs_once" }')
    body+='log = "APDC_CW_VISIBILITY DAY [?apdc_cw_visibility_day] [GetDateText]"\n'
    (driver/'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('on_actions = { on_daily_GER = { effect = { '+body+' } } }','utf-8')
    out=ROOT/'docs/cold-war/20261025-map-display-regression';(out/'after-profile.txt').write_text(str(profile),'utf-8')
    print(json.dumps({'profile':str(profile),'stages':[label for label,action in stages],'pristine_before_suite':True}));return profile

if __name__=='__main__':prepare(sys.argv[1])
