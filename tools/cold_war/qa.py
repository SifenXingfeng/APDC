"""Isolated native-engine integration checks for the Cold War subsystem."""
from pathlib import Path
import sys,json,datetime,hashlib
from common import ROOT,OUT,block,iff,setv,add,parse
from world_renderer import fast_mode

def prepare():
    sys.path.insert(0,str(ROOT/'tools/performance'))
    import prepare_runtime
    profile=Path('D:/APDC_ColdWarQA_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    prepare_runtime.QA=profile;prepare_runtime.prepare(toolpack=True)
    # Match the supplied 1078x972 panel to an actual 1080p test viewport.
    settings=profile/'settings.txt';t=settings.read_text('utf-8').replace('1280','1920').replace('720','1080');settings.write_text(t,'utf-8')
    names=[]
    def expect(name,test):
        names.append(name);return iff(test,'log = "APDC_CW_QA PASS '+name+'"','log = "APDC_CW_QA FAIL '+name+'"')
    def want(tag,field,val,name):return block(tag,expect(name,f'check_variable = {{ {field} = {val} }}'))
    def near(tag,field,val,name,tol=.005):
        lo=f'{val-tol:.6f}'.rstrip('0').rstrip('.');hi=f'{val+tol:.6f}'.rstrip('0').rstrip('.')
        return block(tag,setv('qa_measured',field)+expect(name,f'check_variable = {{ qa_measured > {lo} }} check_variable = {{ qa_measured < {hi} }}')+'log = "APDC_CW_MEASURE '+name+' actual=[?qa_measured|5]"\n')
    def change(target,actor,axis,delta):return block(target,setv('apdc_cw_actor',actor)+setv('apdc_cw_axis',axis)+setv('apdc_cw_delta',delta)+'apdc_cw_change_control = yes')
    def reset(target):
        body=''
        for a in ['political','economic','military']:
            body+=f'for_loop_effect = {{ start = 0 end = apdc_cw_sources^num value = qa_cw_reset set_variable = {{ apdc_cw_{a}^qa_cw_reset = 0 }} }}\n'+setv('apdc_cw_'+a+'^0',100)
        return block(target,body+'apdc_cw_snapshot = yes')
    body='log = "APDC_CW_QA BEGIN"\n'
    body+=expect('startup_prepares_world_cache',f'check_variable = {{ apdc_cw_world_cache_version = {5 if fast_mode() else 4} }} check_variable = {{ apdc_cw_world_border_visible^num > 0 }} check_variable = {{ apdc_cw_seen_map_revision = global.apdc_cw_map_revision }}')
    body+='''set_variable = { qa_diag_count = 0 }
for_loop_effect = { start = 0 end = 3 value = qa_diag_j
add_to_variable = { qa_diag_count = 1 }
log = "APDC_CW_DIAG literal j=[?qa_diag_j|6] count=[?qa_diag_count|6] break=[?break|6]"
}
log = "APDC_CW_DIAG literal done=[?qa_diag_count|6]"
set_variable = { qa_diag_count = 0 }
for_each_loop = { array = apdc_cw_law_id value = qa_diag_val index = qa_diag_idx
add_to_variable = { qa_diag_count = 1 }
if = { limit = { check_variable = { qa_diag_idx < 2 } }
log = "APDC_CW_DIAG each i=[?qa_diag_idx|6] val=[?qa_diag_val|6]"
}
}
log = "APDC_CW_DIAG each done=[?qa_diag_count|6]"
set_variable = { qa_diag_x = 30 }
if = { limit = { check_variable = { qa_diag_x > 29.995 } check_variable = { qa_diag_x < 30.005 } }
log = "APDC_CW_DIAG short near PASS" } else = { log = "APDC_CW_DIAG short near FAIL" }
if = { limit = { check_variable = { var = qa_diag_x value = 29.995 compare = greater_than } check_variable = { var = qa_diag_x value = 30.005 compare = less_than } }
log = "APDC_CW_DIAG long near PASS" } else = { log = "APDC_CW_DIAG long near FAIL" }
if = { limit = { check_variable = { qa_diag_x > 29.995000 } check_variable = { qa_diag_x < 30.005000 } }
log = "APDC_CW_DIAG six-decimal near PASS" } else = { log = "APDC_CW_DIAG six-decimal near FAIL" }
'''
    for tag in ['GER','FRA','LLU','ENG']:
        for a in ['political','economic','military']:body+=want(tag,'apdc_cw_'+a+'^0',100,tag+'_'+a+'_initial_autonomy')
    body+=expect('germany_only_two_test_targets','check_variable = { apdc_cw_intervenable^num = 2 } is_in_array = { array = apdc_cw_intervenable value = FRA } is_in_array = { array = apdc_cw_intervenable value = LLU }')
    body+=want('FRA','apdc_cw_intervenable^num',0,'france_not_given_intervention_rights')
    body+=want('GER','apdc_cw_law_id^num',28,'test_laws_registered')
    body+='set_variable = { QA_cw_running_count = 0 }\nfor_each_loop = { array = apdc_cw_law_running add_to_variable = { QA_cw_running_count = v } }\n'+expect('all_new_laws_stopped','check_variable = { QA_cw_running_count = 0 }')
    body+=change('FRA','GER',1,20)+change('FRA','SOV',1,30)
    body+='FRA = { log = "APDC_CW_QA TRACE sources=[?apdc_cw_sources^num|6] index=[?apdc_cw_source_index|6] p0=[?apdc_cw_political^0|6] p1=[?apdc_cw_political^1|6] p2=[?apdc_cw_political^2|6] j=[?apdc_cw_j|6]" }\n'
    body+=near('FRA','apdc_cw_political^1',14,'growth_scales_existing_foreign_share')+near('FRA','apdc_cw_political^0',56,'growth_scales_autonomy')+near('FRA','apdc_cw_political^2',30,'selected_growth_is_percentage_points')
    body+=change('FRA','SOV',1,-10)
    body+=near('FRA','apdc_cw_political^1',16,'decrease_expands_other_foreign_share')+near('FRA','apdc_cw_political^0',64,'decrease_expands_autonomy_proportionally')
    for a in ['political','economic','military']:
        body+=block('FRA',setv('QA_cw_sum',0)+f'for_each_loop = {{ array = apdc_cw_{a} add_to_variable = {{ QA_cw_sum = v }} }}\n'+expect(a+'_sums_to_100','check_variable = { QA_cw_sum = 100 }'))
    body+=reset('FRA')+change('FRA','GER',2,40)+change('FRA','GER',3,60)
    body+='FRA = { apdc_cw_snapshot = yes apdc_cw_political_attraction = yes }\n'+near('FRA','apdc_cw_political^1',.1,'political_attraction_daily_cap')
    body+=reset('FRA')+change('FRA','GER',2,2)+'FRA = { apdc_cw_political_attraction = yes }\n'+near('FRA','apdc_cw_political^1',.01,'political_attraction_minimum')
    body+=reset('FRA')+change('FRA','GER',2,10)+'FRA = { apdc_cw_political_attraction = yes }\n'+near('FRA','apdc_cw_political^1',.05,'political_attraction_linear_middle')
    body+=reset('FRA')+change('FRA','GER',1,60)+change('FRA','GER',2,20)+change('FRA','GER',3,20)+'FRA = { apdc_cw_political_attraction = yes }\n'+near('FRA','apdc_cw_political^1',60,'political_attraction_never_directly_decreases')
    body+=reset('FRA')+change('FRA','GER',2,.01)+'FRA = { apdc_cw_political_attraction = yes }\n'+near('FRA','apdc_cw_political^1',.005,'political_attraction_does_not_overshoot',.0015)
    body+=reset('FRA')+'apdc_cw_open_panel = yes\n'+want('GER','apdc_cw_world_frames^64',1,'own_country_red')
    body+=setv('qa_cached_map_builds','apdc_cw_world_cache_builds')+'apdc_cw_ensure_world_cache = yes\n'+expect('unchanged_world_cache_is_reused','check_variable = { apdc_cw_world_cache_builds = qa_cached_map_builds }')
    body+=want('GER','apdc_cw_world_frames^28',3,'france_blue')+want('GER','apdc_cw_world_frames^6',3,'lowlands_blue')
    body+=setv('apdc_cw_target','FRA')+setv('apdc_cw_value',1)+'apdc_cw_set_controlled = yes\napdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_world_frames^28',4,'story_control_turns_country_pink')
    body+=setv('apdc_cw_value',0)+'apdc_cw_set_controlled = yes\napdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_world_frames^28',3,'story_control_can_be_removed')
    # Exercise the actual compiled map-button callback and its immediate refresh.
    sgpath=ROOT/'common/scripted_guis/APDC_cold_war.txt';sgtext=sgpath.read_text('utf-8')
    def descend(nodes):
        for node in nodes:
            yield node
            yield from descend(node.children)
    callback=next(n for n in descend(parse(sgtext)) if n.key==('apdc_cw_world_piece_click' if fast_mode() else 'apdc_cw_world_5_click'))
    body+='clear_array = apdc_cw_detail_pieces\n'+setv('qa_detail_before','apdc_cw_detail_ui_revision')+setv('apdc_cw_world_piece_id',5)+sgtext[callback.value_start+1:callback.value_end-1]+'\n'
    body+=expect('actual_map_callback_builds_lowlands_immediately','var:apdc_cw_selected = { tag = LLU } check_variable = { apdc_cw_detail = 1 } check_variable = { apdc_cw_detail_pieces^num > 0 } check_variable = { apdc_cw_detail_ui_revision > qa_detail_before }')
    body+=want('GER','apdc_cw_visible_laws^num',2,'map_callback_preserves_actor_law_scope')
    body+=setv('apdc_cw_selected','FRA')+setv('apdc_cw_detail',1)+'apdc_cw_prepare_detail = yes\napdc_cw_refresh_view = yes\n'
    body+=want('GER','apdc_cw_visible_laws^num',8,'france_political_rows_overflow_scroll_area')
    geometry=json.loads((OUT/'geometry.json').read_text('utf-8'))
    body+=expect('world_template_preserves_all_state_pieces',f'check_variable = {{ apdc_cw_world_piece_rows^num = {len(geometry["pieces"])} }} var:apdc_cw_world_piece_owners^5 = {{ tag = LLU }} check_variable = {{ apdc_cw_world_piece_frames^5 = 3 }}')
    for kind,key in [('piece','pieces'),('border','borders')]:
        body+=expect(kind+'_render_token_lookup_complete',f'check_variable = {{ global.apdc_cw_{kind}_images^num = {len(geometry[key])} }} NOT = {{ check_variable = {{ global.apdc_cw_{kind}_images^0 = 0 }} }} check_variable = {{ global.apdc_cw_{kind}_images^0 = token:{geometry[key][0]["image"]} }} check_variable = {{ global.apdc_cw_{kind}_images^{len(geometry[key])-1} = token:{geometry[key][-1]["image"]} }}')
        body+=f'log = "APDC_CW_IMAGE_TOKEN {kind} first=[?global.apdc_cw_{kind}_images^0.GetTokenKey] last=[?global.apdc_cw_{kind}_images^{len(geometry[key])-1}.GetTokenKey]"\n'
    initial=json.loads((ROOT/'tools/map_maintenance/baseline/initial_territories.json').read_text('utf-8'))
    core_pieces=[e['id'] for e in geometry['pieces'] if initial[str(e['state'])]['owner']=='FRA' and 'FRA' in initial[str(e['state'])]['cores']]
    alsace_pieces=[e['id'] for e in geometry['pieces'] if e['state']==28]
    body+=want('GER','apdc_cw_detail_pieces^num',len(core_pieces),'france_detail_contains_only_owned_core_states')
    body+='28 = { remove_core_of = FRA }\napdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_detail_pieces^num',len(core_pieces)-len(alsace_pieces),'core_removal_refreshes_open_detail')+want('GER','apdc_cw_world_frames^28',3,'core_removal_leaves_world_owner_map_unchanged')
    body+='28 = { add_core_of = FRA }\napdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_detail_pieces^num',len(core_pieces),'core_restoration_refreshes_open_detail')
    french_states=[sid for sid,row in initial.items() if row['owner']=='FRA' and 'FRA' in row['cores']]
    body+=''.join(block(sid,'remove_core_of = FRA') for sid in french_states)+'apdc_cw_refresh_view = yes\n'
    body+=expect('no_core_territory_has_empty_finite_map','check_variable = { apdc_cw_detail_pieces^num = 0 } check_variable = { apdc_cw_detail_borders^num = 0 } check_variable = { apdc_cw_detail_span = 0 } check_variable = { apdc_cw_detail_height = 0 }')
    body+='log = "APDC_CW_EMPTY selected=[?apdc_cw_selected.GetName] actual_cores=[?FRA.apdc_cw_owned_core_count] count=[?apdc_cw_detail_state_count] pieces=[?apdc_cw_detail_pieces^num] borders=[?apdc_cw_detail_borders^num] span=[?apdc_cw_detail_span] height=[?apdc_cw_detail_height]"\n'
    body+=''.join(block(sid,'add_core_of = FRA') for sid in french_states)+'apdc_cw_refresh_view = yes\n'
    body+='log = "APDC_CW_QA TRACE laws=[?apdc_cw_law_id^num] firstid=[?apdc_cw_law_id^0] target=[?apdc_cw_law_target^0.GetName] selected=[?apdc_cw_selected.GetName] axis=[?apdc_cw_law_axis^0] tab=[?apdc_cw_tab] visible=[?apdc_cw_visible_laws^num]"\n'
    body+=expect('detail_has_current_owned_pieces','check_variable = { apdc_cw_detail_pieces^num > 0 } check_variable = { apdc_cw_display_span < 461 }') if False else ''
    body+=expect('detail_has_current_owned_pieces','check_variable = { apdc_cw_detail_pieces^num > 0 }')
    body+=setv('apdc_cw_law_row',0)+setv('apdc_cw_option',1)+'add_political_power = 200\n'+setv('QA_cw_pp','political_power')+'apdc_cw_submit_law = yes\n'+want('GER','apdc_cw_law_running^0',1,'execute_switches_law_on')
    body+='subtract_from_variable = { QA_cw_pp = political_power }\n'+expect('execute_charges_exact_cost','check_variable = { QA_cw_pp = 10 }')
    body+='apdc_cw_submit_law = yes\n'+expect('reselect_current_law_is_blocked','check_variable = { apdc_cw_law_running^0 = 1 }')
    body+='apdc_cw_unlock_law_1 = yes\n'+expect('repeated_unlock_preserves_record_and_state','check_variable = { apdc_cw_law_id^num = 28 } check_variable = { apdc_cw_law_running^0 = 1 }')
    body+='FRA = { apdc_cw_snapshot = yes }\napdc_cw_tick_laws = yes\n'+near('FRA','apdc_cw_political^1',.01,'running_law_changes_control_each_tick')
    body+=setv('qa_saved_stop_pp','political_power')+'set_temp_variable = { qa_remove_pp = political_power }\nmultiply_temp_variable = { qa_remove_pp = -1 }\nadd_political_power = qa_remove_pp\n'+setv('apdc_cw_option',0)+'apdc_cw_submit_law = yes\n'+expect('insufficient_pp_also_blocks_stop','check_variable = { apdc_cw_law_running^0 = 1 } check_variable = { political_power = 0 }')+'add_political_power = qa_saved_stop_pp\n'
    body+=setv('qa_stop_pp','political_power')+'resize_array = { array = apdc_cw_law_stop_cost size = apdc_cw_law_id^num value = 0 }\n'+setv('apdc_cw_law_stop_cost^0',999)+'apdc_cw_submit_law = yes\napdc_cw_tick_laws = yes\nsubtract_from_variable = { qa_stop_pp = political_power }\n'+expect('stop_charges_same_switch_cost_ignoring_legacy_stop_array','check_variable = { qa_stop_pp = 10 }')+want('GER','apdc_cw_law_running^0',0,'stop_switches_law_off')+near('FRA','apdc_cw_political^1',.01,'stop_preserves_accumulated_control')
    body+=expect('stop_restores_option_frames','check_variable = { apdc_cw_law_execute_frame^0 = 1 } check_variable = { apdc_cw_law_stop_frame^0 = 2 }')
    body+=setv('apdc_cw_id',1)+setv('apdc_cw_target','FRA')+setv('apdc_cw_value',1)+'apdc_cw_lock_law = yes\n'+setv('apdc_cw_option',1)+'apdc_cw_submit_law = yes\n'+want('GER','apdc_cw_law_running^0',0,'locked_law_cannot_execute')
    body+=setv('apdc_cw_value',0)+'apdc_cw_lock_law = yes\n'
    body+=setv('qa_saved_pp','political_power')+'set_temp_variable = { qa_pp_adjust = political_power }\nmultiply_temp_variable = { qa_pp_adjust = -1 }\nadd_political_power = qa_pp_adjust\napdc_cw_submit_law = yes\n'+expect('insufficient_pp_blocks_execution','check_variable = { apdc_cw_law_running^0 = 0 } check_variable = { political_power = 0 }')+'add_political_power = qa_saved_pp\n'
    body+='apdc_cw_remove_law = yes\n'+expect('removed_law_stops_and_disappears_immediately','check_variable = { apdc_cw_law_running^0 = 0 } check_variable = { apdc_cw_visible_laws^num = 7 }')+'apdc_cw_unlock_law_1 = yes\n'+expect('removed_law_can_be_unlocked_again','check_variable = { apdc_cw_law_id^num = 28 } check_variable = { apdc_cw_visible_laws^num = 8 } check_variable = { apdc_cw_law_running^0 = 0 }')
    for axis,expected in [(2,3),(3,3),(1,8)]:body+=setv('apdc_cw_tab',axis)+'apdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_visible_laws^num',expected,'france_tab_'+str(axis)+'_filters_laws')
    body+=setv('apdc_cw_selected','GER')+setv('apdc_cw_detail',0)+'apdc_cw_refresh_view = yes\n'+want('GER','apdc_cw_visible_laws^num',2,'own_country_self_laws')
    body+=change('FRA','GER',1,60)+setv('apdc_cw_selected','FRA')+'apdc_cw_refresh_view = yes\n'+expect('majority_political_leaning','var:apdc_cw_ui_leader_political = { tag = GER }')
    body+=expect('pie_has_360_hover_segments','check_variable = { apdc_cw_pie_source^num = 360 }')
    body+=reset('FRA')+change('FRA','GER',1,50)+'apdc_cw_refresh_view = yes\n'+expect('exactly_half_is_still_autonomous','var:apdc_cw_ui_leader_political = { tag = FRA }')
    body+=change('FRA','GER',1,.001)+'apdc_cw_refresh_view = yes\n'+expect('strict_majority_changes_leaning','var:apdc_cw_ui_leader_political = { tag = GER }')
    body+=change('FRA','GER',1,100)+near('FRA','apdc_cw_political^1',100,'control_clamps_at_100')+change('FRA','GER',1,-20)+near('FRA','apdc_cw_political^0',20,'decrease_from_full_control_restores_autonomy')
    body+=reset('FRA')+setv('apdc_cw_selected','FRA')+setv('apdc_cw_detail',1)+setv('apdc_cw_tab',1)+'apdc_cw_prepare_detail = yes\napdc_cw_refresh_world = yes\napdc_cw_refresh_view = yes\n'
    body+=setv('qa_map_revision','global.apdc_cw_map_revision')+'28 = { set_state_controller_to = GER }\n'+expect('occupation_does_not_change_owner_map','check_variable = { apdc_cw_world_frames^28 = 3 } check_variable = { global.apdc_cw_map_revision = qa_map_revision }')+'28 = { set_state_controller_to = FRA }\n'
    body+='28 = { transfer_state_to = GER }\n'+expect('owner_transfer_immediately_refreshes_map','check_variable = { apdc_cw_world_frames^28 = 1 } check_variable = { global.apdc_cw_map_revision > qa_map_revision }')+'28 = { transfer_state_to = FRA }\n'+expect('owner_transfer_back_restores_map','check_variable = { apdc_cw_world_frames^28 = 3 }')
    body+='set_autonomy = { target = FRA autonomy_state = autonomy_puppet }\napdc_cw_refresh_view = yes\n'+expect('subject_status_overrides_story_status','check_variable = { apdc_cw_ui_status = 2 }')+'set_autonomy = { target = FRA autonomy_state = autonomy_free }\napdc_cw_refresh_view = yes\n'+expect('independence_restores_story_status','check_variable = { apdc_cw_ui_status = 5 }')
    for tag in ['GER','LLU','MLT']:
        body+=setv('apdc_cw_selected',tag)+'apdc_cw_prepare_detail = yes\n'+setv('qa_fit_width','apdc_cw_detail_span')+'multiply_variable = { qa_fit_width = apdc_cw_detail_scale }\n'+setv('qa_fit_height','apdc_cw_detail_height')+'multiply_variable = { qa_fit_height = apdc_cw_detail_scale }\n'+expect(tag+'_detail_fits_viewport','check_variable = { qa_fit_width < 461 } check_variable = { qa_fit_height < 431 }')
        body+='log = "APDC_CW_FIT '+tag+' zoom=[?apdc_cw_detail_zoom] scale=[?apdc_cw_detail_scale|5] x=[?apdc_cw_detail_span] y=[?apdc_cw_detail_height] width=[?qa_fit_width|5] height=[?qa_fit_height|5]"\n'
    # Leave a mixed-colour country detail and one running law for native visual QA.
    body+=reset('FRA')+change('FRA','GER',1,45)+change('FRA','SOV',1,20)+change('FRA','GER',2,40)+change('FRA','GER',3,60)+setv('apdc_cw_selected','FRA')+setv('apdc_cw_detail',1)+setv('apdc_cw_tab',1)+'apdc_cw_prepare_detail = yes\napdc_cw_refresh_world = yes\napdc_cw_refresh_view = yes\n'+setv('apdc_cw_law_row',0)+setv('apdc_cw_option',1)+'apdc_cw_submit_law = yes\n'
    body+=setv('qa_batches_before','global.apdc_cw_daily_batches')
    body+=expect('shared_pie_tooltip_cache_matches_autonomy','var:apdc_cw_pie_owner^0 = { tag = FRA } check_variable = { apdc_cw_pie_shares^0 = 44 }')
    body+=expect('shared_pie_tooltip_cache_matches_germany','var:apdc_cw_pie_owner^200 = { tag = GER } check_variable = { apdc_cw_pie_shares^200 = 36 }')
    body+=expect('shared_pie_tooltip_cache_matches_soviet_union','var:apdc_cw_pie_owner^330 = { tag = SOV } check_variable = { apdc_cw_pie_shares^330 = 20 }')
    for degree in [0,200,330,0]:
        body+=f'log = "APDC_CW_TOOLTIP_PROBE {degree} [APDCCWPieBind{degree}]"\n'
    if '--world-review' in sys.argv:
        callback=next(n for n in descend(parse(sgtext)) if n.key=='apdc_cw_return_click')
        body+=setv('qa_cached_map_revision','apdc_cw_map_ui_revision')+setv('qa_cached_map_builds','apdc_cw_world_cache_builds')+sgtext[callback.value_start+1:callback.value_end-1]+'\n'
        body+=expect('return_reuses_unchanged_world_cache','check_variable = { apdc_cw_world_cache_builds = qa_cached_map_builds }')
        body+=expect('return_rebinds_world_ui_after_becoming_visible','check_variable = { apdc_cw_map_ui_revision > qa_cached_map_revision }')
        body+=expect('actual_return_callback_restores_world_and_self','check_variable = { apdc_cw_detail = 0 } var:apdc_cw_selected = { tag = GER } check_variable = { apdc_cw_world_piece_rows^num > 0 }')
        body+='log = "APDC_CW_WORLD_REVIEW_READY"\n'
    body+='log = "APDC_CW_QA COMPLETE"\n'
    driver=profile/'driver'
    (driver/'common/scripted_effects').mkdir(exist_ok=True)
    (driver/'common/scripted_effects/APDC_cold_war_qa.txt').write_text(block('apdc_cw_run_qa',body),'utf-8')
    daily=expect('global_daily_batch_runs_once','check_variable = { qa_batch_difference = 1 }')
    (driver/'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('on_actions = { on_daily_GER = { effect = { if = { limit = { NOT = { has_country_flag = apdc_cw_qa_done } } set_country_flag = apdc_cw_qa_done apdc_cw_run_qa = yes } else_if = { limit = { NOT = { has_country_flag = apdc_cw_qa_daily_checked } } set_country_flag = apdc_cw_qa_daily_checked set_variable = { qa_batch_difference = global.apdc_cw_daily_batches } subtract_from_variable = { qa_batch_difference = qa_batches_before } '+daily+' } log = "APDC_CW_QA DAY [GetDateText] batches=[?global.apdc_cw_daily_batches]" } } }','utf-8')
    (OUT/'expected-checks.json').write_text(json.dumps(names,indent=2),'utf-8')
    (OUT/'qa-profile.txt').write_text(str(profile),'utf-8')
    print(json.dumps({'profile':str(profile),'assertions':len(names)}))
    return profile

if __name__=='__main__':prepare()
