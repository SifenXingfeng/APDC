"""Prepare or inspect isolated native-content tests; never launch a game."""
from pathlib import Path
import argparse,json,re,hashlib,shutil

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/tooling/20261110-native-content-api'
PROFILE=Path.home()/'.codex/tmp/APDC_native_content_20261110'
def put(p,s,bom=False):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+'\n',encoding='utf-8-sig' if bom else 'utf-8')
def b(k,s):return k+' = {\n'+s+'\n}\n'
def v(k,x,temp=False):return f'set_{"temp_" if temp else ""}variable = {{ {k} = {x} }}\n'
def cv(k,x,op='='):return f'check_variable = {{ {k} {op} {x} }}'
def check(name,test):return b('if','limit = { '+test+' }\nlog = "APDC_CONTENT_QA PASS '+name+'"')+b('else','log = "APDC_CONTENT_QA FAIL '+name+'"')

def candidate(i):
    prefix=f'apdc_candidate_{i}'
    setup=v('apdc_nc_name','token:qa_content_candidate',True)+v('apdc_nc_portrait','token:GFX_leader_unknown',True)+v('apdc_nc_member_text','token:qa_content_member',True)+v('apdc_nc_chief_text','token:qa_content_chief',True)+v('apdc_nc_character','token:GER_APDC_romy_riefenstahl',True)+v('apdc_nc_party',2,True)+v('apdc_nc_visible',1,True)
    setup+=b('if','limit = { has_country_flag = qa_content_block_candidate }\n'+v('apdc_nc_available',0,True))
    return b(prefix+'_setup',setup)+b(prefix+'_on_appoint_member','add_to_variable = { qa_content_member_balance = 1 }')+b(prefix+'_on_remove_member','add_to_variable = { qa_content_member_balance = -1 }')+b(prefix+'_on_appoint_chief','add_to_variable = { qa_content_chief_balance = 1 }')+b(prefix+'_on_remove_chief','add_to_variable = { qa_content_chief_balance = -1 }')

def action(i,axis=1,target='FRA',beneficiary='GER'):
    setup=''.join(v('apdc_cw_'+k,x) for k,x in {'target':target,'axis':axis,'beneficiary':beneficiary,'rate':0.1,'execute_cost':5,'self':int(target=='GER')}.items())
    setup+=v('apdc_na_name','token:qa_content_action',True)+v('apdc_na_desc','token:qa_content_action_desc',True)+b('if','limit = { has_country_flag = qa_content_block_action }\n'+v('apdc_na_available',0,True))
    prefix=f'apdc_cw_action_{i}'
    return b(prefix+'_setup',setup)+''.join(b(prefix+'_on_'+phase,'add_to_variable = { qa_content_action_'+phase+' = 1 }') for phase in ['execute','stop','daily'])

def rule(i):
    setup=v('APDC_cooperation_new_law_group_tab',1,True)+v('APDC_cooperation_new_law_group_option_count',2,True)+v('APDC_cooperation_new_law_group_default_option',1,True)+v('apdc_nr_name','token:qa_content_rule',True)
    setup+=b('if','limit = { has_country_flag = qa_content_hide_rule }\n'+v('apdc_nr_visible',0,True))
    setup+=b('if','limit = { has_country_flag = qa_content_block_rule }\n'+v('apdc_nr_option_2_available',0,True))
    for opt in [1,2]:setup+=v(f'apdc_nr_option_{opt}_name','token:qa_content_rule_option_'+str(opt),True)+v(f'apdc_nr_option_{opt}_effect','token:qa_content_rule_effect_'+str(opt),True)
    prefix=f'apdc_cooperation_rule_{i}'
    return b(prefix+'_setup',setup)+b(prefix+'_on_enact','add_to_variable = { qa_content_rule_enact = 1 }')+b(prefix+'_on_repeal','add_to_variable = { qa_content_rule_repeal = 1 }')+b(prefix+'_on_member_apply','add_to_variable = { qa_content_rule_member_balance = 1 }')+b(prefix+'_on_member_remove','add_to_variable = { qa_content_rule_member_balance = -1 }')+b(prefix+'_on_fail','add_to_variable = { qa_content_rule_fail = 1 }')

def prepare(profile):
    REPORT.mkdir(parents=True,exist_ok=True);driver=profile/'driver'
    if (driver/'common/on_actions/AAA_native_content_after_save.txt').exists():
        raise SystemExit('This profile contains a completed later-content test. Use --profile with a new private directory.')
    desc=(ROOT/'descriptor.mod').read_text('utf-8-sig');desc=re.sub(r'^path=.*$',lambda m:'path="'+ROOT.as_posix()+'"',desc,flags=re.M)
    put(profile/'mod/APDC.mod',desc)
    put(profile/'mod/APDC_NativeContentQA.mod','name="APDC Native Content QA"\npath="'+driver.as_posix()+'"\ndependencies={ "少女前线-APDC" }\nsupported_version="1.19.*"')
    user=Path.home()/'Documents/Paradox Interactive/Hearts of Iron IV';dlc=json.loads((user/'dlc_load.json').read_text('utf-8-sig'))
    put(profile/'dlc_load.json',json.dumps({'enabled_mods':['mod/APDC.mod','mod/APDC_NativeContentQA.mod'],'disabled_dlcs':dlc.get('disabled_dlcs',[])}))
    for name in ['settings.txt','pdx_settings.txt']:
        source=Path.home()/'.codex/tmp/APDC_CountryQA_20261028_final/parliament_native_20261110'/name
        put(profile/name,source.read_text('utf-8-sig'))
    put(driver/'common/defines/zzzz_apdc_native_content_qa.lua','NDefines.NGame.GAME_SPEED_SECONDS = { 0.05, 0.05, 0.05, 0.05, 0.0 }')
    for i in [2001,2002]:put(driver/f'common/scripted_effects/qa_independent_candidate_{i}.txt',candidate(i))
    for i,axis,target,actor in [(1001,1,'FRA','GER'),(1002,2,'GER','GER'),(1003,3,'GER','SOV')]:put(driver/f'common/scripted_effects/qa_independent_action_{i}.txt',action(i,axis,target,actor))
    put(driver/'common/scripted_effects/qa_independent_rule_101.txt',rule(101))
    keys={'qa_content_candidate':'独立候选人','qa_content_member':'成员特质','qa_content_chief':'首席特质','qa_content_action':'独立冷战行动','qa_content_action_desc':'不运行生成器的冷战行动','qa_content_rule':'独立组织规则','qa_content_rule_option_1':'规则选项一','qa_content_rule_option_2':'规则选项二','qa_content_rule_effect_1':'选项一效果','qa_content_rule_effect_2':'选项二效果'}
    put(driver/'common/synchronized_dynamic_tokens/qa_content_tokens.txt','\n'.join(keys)+'\nGFX_leader_unknown\nGER_APDC_romy_riefenstahl')
    put(driver/'localisation/simp_chinese/qa_content_l_simp_chinese.yml','l_simp_chinese:\n'+''.join(' '+k+':0 "'+x+'"\n' for k,x in keys.items()),True)
    body='log = "APDC_CONTENT_QA BEGIN"\nset_political_power = 2000\napdc_parl_enact_political_system_1 = yes\nAPDC_add_socialism_to_governing_coalition = yes\n'+v('apdc_parl_winner_socialism',1)
    for r in range(1,9):body+=f'apdc_parl_clear_role_{r} = yes\n'
    body+='APDC_update_cabinet_statistics = yes\n'+v('qa_content_roster_before','apdc_nc_ids^num')
    body+=v('apdc_nc_id',2001,True)+'apdc_register_candidate = yes\napdc_register_candidate = yes\n'+v('qa_content_roster_expected','qa_content_roster_before')+'add_to_variable = { qa_content_roster_expected = 1 }\n'
    body+=check('candidate_registration_idempotent',cv('apdc_nc_ids^num','qa_content_roster_expected'))
    body+=v('apdc_parl_selected_role',1)+v('apdc_parl_selected_candidate',2001)+'apdc_parl_appoint_selected = yes\n'
    body+=check('new_candidate_member_effect_and_slot',cv('APDC_cabinet_slot_1',2001)+' '+cv('qa_content_member_balance',1))
    body+=v('apdc_nc_id',2002,True)+'apdc_register_candidate = yes\n'+v('apdc_parl_selected_role',2)+v('apdc_parl_selected_candidate',2002)+'apdc_parl_appoint_selected = yes\n'
    body+=check('same_character_cannot_hold_two_offices',cv('APDC_cabinet_slot_1',0)+' '+cv('APDC_cabinet_slot_2',2002)+' '+cv('qa_content_member_balance',1))
    body+='set_country_flag = qa_content_block_candidate\n'+v('apdc_parl_selected_role',3)+'apdc_parl_appoint_selected = yes\n'
    body+=check('candidate_condition_guards_direct_appointment',cv('APDC_cabinet_slot_3',0)+' '+cv('APDC_cabinet_slot_2',2002))
    body+='clr_country_flag = qa_content_block_candidate\n'+v('apdc_parl_selected_role',7)+v('apdc_parl_free_prime',1)+'apdc_parl_appoint_selected = yes\n'
    body+=check('native_candidate_can_become_chief',cv('apdc_parl_role_7',2002)+' '+cv('qa_content_chief_balance',1)+' '+cv('qa_content_member_balance',0))
    body+='apdc_parl_dismiss_selected = yes\n'+check('candidate_removal_callback',cv('qa_content_chief_balance',0)+' '+cv('apdc_parl_role_7',0))
    body+=v('qa_content_actions_before','apdc_cw_law_id^num')+v('apdc_na_id',1001,True)+'apdc_unlock_cold_war_action = yes\napdc_unlock_cold_war_action = yes\n'+v('qa_content_actions_expected','qa_content_actions_before')+'add_to_variable = { qa_content_actions_expected = 1 }\n'
    body+=check('action_registration_idempotent',cv('apdc_cw_law_id^num','qa_content_actions_expected'))
    body+=v('apdc_cw_law_row','apdc_cw_law_index')+v('qa_content_action_row','apdc_cw_law_index')+v('apdc_cw_option',1)+'apdc_cw_submit_law = yes\n'
    body+=check('action_execute_callback',cv('qa_content_action_execute',1)+' '+cv('apdc_cw_law_running^qa_content_action_row',1))
    body+='apdc_cw_tick_laws = yes\n'+check('action_daily_callback_and_rate',cv('qa_content_action_daily',1)+' '+cv('apdc_cw_law_last_delta^qa_content_action_row',0.1))
    body+=v('apdc_cw_selected','FRA')+v('apdc_cw_tab',1)+'apdc_cw_refresh_view = yes\n'+check('dynamic_action_contribution_is_cached',cv('apdc_na_source_names^num',1))
    body+=v('apdc_na_source_cursor',0,True)+v('apdc_na_hover_actor','GER',True)+'log = "APDC_CONTENT_QA SOURCE_TEXT [APDCNativeCWSourceLines]"\n'
    body+=v('apdc_cw_law_row','qa_content_action_row')+v('apdc_cw_option',0)+'apdc_cw_submit_law = yes\napdc_cw_submit_law = yes\n'
    body+=check('action_stop_callback_exactly_once',cv('qa_content_action_stop',1)+' '+cv('apdc_cw_law_running^qa_content_action_row',0))
    body+='set_country_flag = qa_content_block_action\n'+v('apdc_cw_option',1)+'apdc_cw_submit_law = yes\n'+check('action_dynamic_availability_guards_direct_call',cv('apdc_cw_law_running^qa_content_action_row',0))+'clr_country_flag = qa_content_block_action\n'
    body+=v('apdc_na_id',1001,True)+v('apdc_cw_target','FRA')+'apdc_execute_cold_war_action = yes\n'+v('apdc_na_id',1001,True)+v('apdc_cw_target','FRA')+'apdc_remove_cold_war_action = yes\napdc_remove_cold_war_action = yes\n'
    body+=check('action_removal_stops_effect_exactly_once',cv('qa_content_action_stop',2)+' '+cv('apdc_cw_law_unlocked^qa_content_action_row',0))
    for i in [1002,1003]:body+=v('apdc_na_id',i,True)+'apdc_unlock_cold_war_action = yes\n'+v('apdc_cw_law_row','apdc_cw_law_index')+v('apdc_cw_option',1)+'apdc_cw_submit_law = yes\n'
    body+=check('all_three_axes_and_domestic_actions_register',cv('apdc_cw_law_axis^apdc_cw_law_row',3)+' '+cv('apdc_cw_law_running^apdc_cw_law_row',1))
    org='APDC_create_fifth_international_cooperation_organization_from_template = yes\n'+v('apdc_nr_id',101,True)+'apdc_register_organization_rule = yes\napdc_register_organization_rule = yes\n'
    org+=check('rule_registration_applies_default_once',cv('qa_content_rule_enact',1)+' '+cv('APDC_cooperation_container_law_selected_options^101',1))
    org+=v('APDC_cooperation_container_active_law_group',101)+v('APDC_cooperation_container_active_law_option',2)+'clear_array = APDC_cooperation_container_vote_supporters\nclear_array = APDC_cooperation_container_vote_vetoers\nadd_to_array = { APDC_cooperation_container_vote_supporters = SOV }\nAPDC_resolve_cooperation_law_vote_container = yes\n'
    org+=check('rule_pass_repeals_old_and_enacts_new',cv('APDC_cooperation_container_law_selected_options^101',2)+' '+cv('qa_content_rule_repeal',1)+' '+cv('qa_content_rule_enact',2))
    org+=v('apdc_nr_id',101,True)+v('APDC_cooperation_container_law_group_locks^101',1)+'apdc_register_organization_rule = yes\n'
    org+=check('rule_reregistration_preserves_selection_and_lock',cv('APDC_cooperation_container_law_selected_options^101',2)+' '+cv('APDC_cooperation_container_law_group_locks^101',1)+' '+cv('qa_content_rule_enact',2))
    org+=v('APDC_cooperation_container_active_law_group',101)+v('APDC_cooperation_container_active_law_option',1)+'clear_array = APDC_cooperation_container_vote_supporters\nadd_to_array = { APDC_cooperation_container_vote_vetoers = SOV }\nAPDC_resolve_cooperation_law_vote_container = yes\n'
    org+=check('rule_failure_calls_callback_and_keeps_old_effect',cv('qa_content_rule_fail',1)+' '+cv('APDC_cooperation_container_law_selected_options^101',2)+' '+cv('qa_content_rule_enact',2))
    org+='set_country_flag = qa_content_block_rule\nAPDC_sync_cooperation_organization_all_member_scalar_views = yes\n'+check('rule_conditions_refresh_without_re_registration',cv('APDC_cooperation_container_law_option_2_available^101',0))+'clr_country_flag = qa_content_block_rule\n'
    org+='set_country_flag = qa_content_hide_rule\nAPDC_sync_cooperation_organization_all_member_scalar_views = yes\n'+check('rule_visibility_refreshes_without_rebuild',cv('apdc_nr_visibles^101',0))+'clr_country_flag = qa_content_hide_rule\nAPDC_sync_cooperation_organization_all_member_scalar_views = yes\n'
    body+=b('SOV',org)
    body+=check('rule_member_effects_stay_balanced',cv('qa_content_rule_member_balance',1))
    body+='APDC_leave_cooperation_organization = yes\n'+check('leaving_organization_removes_rule_effects',cv('qa_content_rule_member_balance',0))
    body+=v('APDC_cooperation_organization_join_target','SOV')+'APDC_join_cooperation_organization = yes\n'+v('APDC_cooperation_organization_join_target','SOV')+'APDC_join_cooperation_organization = yes\n'
    body+=check('joining_applies_current_rule_once',cv('qa_content_rule_member_balance',1))
    body+=v('APDC_cooperation_law_group_id',101)+'log = "APDC_CONTENT_QA RULE_NAME [APDCCooperationLawGroupName]"\n'
    body+='clear_array = apdc_na_source_names\nclear_array = apdc_na_source_deltas\nclear_array = apdc_na_source_actors\n'
    body+=b('for_loop_effect','start = 0 end = 80 value = qa_content_source_test\nadd_to_array = { apdc_na_source_names = token:qa_content_action }\nadd_to_array = { apdc_na_source_deltas = 0.01 }\nadd_to_array = { apdc_na_source_actors = GER }')
    body+=v('apdc_na_source_cursor',0,True)+v('apdc_na_hover_actor','GER',True)+'log = "APDC_CONTENT_QA SOURCE_STRESS [APDCNativeCWSourceLines] SOURCE_STRESS_END"\n'
    destroy=v('APDC_cooperation_organization_definition_id',999)+'APDC_create_cooperation_organization = yes\n'+v('APDC_cooperation_organization_join_target','ITA')+'APDC_join_cooperation_organization = yes\n'+v('apdc_nr_id',101,True)+'apdc_register_organization_rule = yes\nAPDC_remove_cooperation_organization = yes\n'
    destroy+=check('organization_disband_repeals_anchor_and_member_effects',cv('qa_content_rule_repeal',1)+' '+cv('qa_content_rule_member_balance',0)+' NOT = { APDC_has_cooperation_organization = yes }')
    body+=b('ITA',destroy)
    # Keep one new candidate, two actions and a nondefault rule in the real save.
    body+=v('apdc_parl_selected_role',7)+v('apdc_parl_selected_candidate',2002)+v('apdc_parl_free_prime',1)+'apdc_parl_appoint_selected = yes\n'+v('apdc_cw_selected','GER')+v('apdc_cw_tab',3)+'apdc_cw_refresh_view = yes\nset_country_flag = qa_content_initial_done\nlog = "APDC_CONTENT_QA END"\n'
    put(driver/'common/scripted_effects/qa_native_content_tests.txt',b('qa_native_content_run',body))
    put(driver/'common/on_actions/zzzz_native_content_tests.txt',b('on_actions',b('on_daily_GER',b('effect',b('if','limit = { NOT = { has_country_flag = qa_content_initial_done } }\nqa_native_content_run = yes')))))
    manifest={'profile':str(profile),'driver':str(driver),'expected_checks':re.findall(r'APDC_CONTENT_QA PASS ([A-Za-z0-9_]+)',body),'core_built_after_test_content':False}
    put(REPORT/'qa-plan.json',json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps(manifest,ensure_ascii=False))

def verify(profile):
    plan=json.loads((REPORT/'qa-plan.json').read_text('utf-8'));log=(profile/'logs/game.log').read_text('utf-8-sig',errors='replace');errors=(profile/'logs/error.log').read_text('utf-8-sig',errors='replace')
    passed=set(re.findall(r'APDC_CONTENT_QA PASS (\w+)',log));failed=re.findall(r'APDC_CONTENT_QA FAIL (\w+)',log);missing=sorted(set(plan['expected_checks'])-passed)
    related=[x for x in errors.splitlines() if any(k.lower() in x.lower() for k in ['apdc_nc','apdc_na_','apdc_nr_','apdc_candidate','apdc_cooperation_rule','apdc_cw_action','native_content','native_candidates','native_cold_war','native_organization','qa_content'])]
    text_match=re.search(r'APDC_CONTENT_QA SOURCE_STRESS (.*?) SOURCE_STRESS_END',log,re.S)
    localized_sources=text_match.group(1).count('独立冷战行动') if text_match else 0
    if localized_sources!=80:failed.append('all_80_contribution_lines_localize')
    if 'APDC_CONTENT_QA RULE_NAME 独立组织规则' not in log:failed.append('independent_rule_name_localizes')
    if not re.search(r'APDC_CONTENT_QA SOURCE_TEXT\s+独立冷战行动',log):failed.append('independent_action_source_name_localizes')
    related += [x for x in errors.splitlines() if 'dynamic token' in x and any(k in x for k in ['GER_APDC_romy_riefenstahl','qa_content','Token HAI_mirlande_dieudonne','Token JAP_fuji_yuko'])]
    out={'status':'passed' if not failed+missing+related else 'failed','passed':sorted(passed),'failed':failed,'missing':missing,'related_errors':related,'localized_contribution_lines':localized_sources,'log_sha256':hashlib.sha256(log.encode()).hexdigest()}
    put(REPORT/'initial-runtime.json',json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False));return out['status']=='passed'

def late_content(profile):
    """Add new providers to an actual save without modifying the core."""
    driver=profile/'driver';save=profile/'save games/autosave.hoi4'
    assert save.is_file(),'An actual saved initial test is required.'
    saved=save.read_text('utf-8-sig');assert 'qa_content_initial_done' in saved
    old_name=int(re.search(r'\bapdc_nc_role_name_7=(\d+)',saved)[1])
    snapshot=profile/'save games/native-before-late.hoi4';shutil.copyfile(save,snapshot)
    for name in ['game.log','error.log']:
        if not (REPORT/('initial-'+name)).exists():
            shutil.copyfile(profile/'logs'/name,REPORT/('initial-'+name))
    for name in ['silent-process.json','silent-stop.json']:
        if not (REPORT/('initial-'+name)).exists():
            shutil.copyfile(profile/name,REPORT/('initial-'+name))
    put(driver/'common/scripted_effects/AAA_native_candidate_after_save.txt',candidate(2003).replace('token:qa_content_candidate','token:qa_added_candidate').replace('qa_content_member_balance','qa_added_member_balance').replace('qa_content_chief_balance','qa_added_chief_balance'))
    put(driver/'common/scripted_effects/AAA_native_legacy_candidate_probe.txt',candidate(2004))
    put(driver/'common/scripted_effects/AAA_native_action_after_save.txt',action(1004,2).replace('token:qa_content_action_desc','token:qa_added_action_desc').replace('token:qa_content_action','token:qa_added_action').replace('qa_content_action_','qa_added_action_'))
    put(driver/'common/scripted_effects/AAA_native_rule_after_save.txt',rule(102).replace('qa_content_rule','qa_added_rule'))
    keys={'qa_added_candidate':'读档新增候选人','qa_added_action':'读档新增冷战行动','qa_added_action_desc':'无须重建的新增内容','qa_added_rule':'读档新增组织规则','qa_added_rule_option_1':'新增选项一','qa_added_rule_option_2':'新增选项二','qa_added_rule_effect_1':'新增效果一','qa_added_rule_effect_2':'新增效果二'}
    put(driver/'common/synchronized_dynamic_tokens/AAA_native_content_after_save.txt','\n'.join(keys))
    put(driver/'localisation/simp_chinese/AAA_native_content_after_save_l_simp_chinese.yml','l_simp_chinese:\n'+''.join(' '+k+':0 "'+value+'"\n' for k,value in keys.items()),True)
    body='log = "APDC_CONTENT_RELOAD BEGIN"\nset_political_power = 2000\n'
    # A saved pre-API country has normal slots/roles, but no native registry.
    # Simulate only those absent caches, preserving real legacy office IDs.
    baseline=json.loads((ROOT/'tools/parliament/data/candidates.json').read_text('utf-8'))['candidates']
    bra=[x['id'] for x in baseline if 'BRA' in x['countries']];assert bra
    legacy_bra='clr_country_flag = apdc_native_candidates_v1\nclr_country_flag = apdc_nc_baseline_registered_v1\nclear_array = apdc_nc_ids\n'+v('APDC_cabinet_slot_1',bra[0])+v('apdc_parl_role_1',bra[0])+v('apdc_nc_id',2004,True)+'apdc_register_candidate = yes\n'
    legacy_bra+=check_reload('legacy_candidate_cache_adopts_original_roster_and_keeps_new_argument',cv('apdc_nc_ids^num',len(bra)+2)+' is_in_array = { array = apdc_nc_ids value = 2004 }')
    legacy_bra+=check_reload('legacy_candidate_adoption_keeps_offices_and_finishes_once',cv('APDC_cabinet_slot_1',bra[0])+' '+cv('apdc_parl_role_1',bra[0])+' '+cv('apdc_nc_ensure_inputs^num',0)+' has_country_flag = apdc_nc_baseline_registered_v1')
    body+=b('BRA',legacy_bra)
    # Original organization saves own their selected rules and explicit locks,
    # but lack metadata/native markers. Adoption must not reset those records.
    legacy_org=v('APDC_cooperation_organization_definition_id',999)+'APDC_create_cooperation_organization = yes\n'+v('APDC_cooperation_organization_join_target','ITA')+'APDC_join_cooperation_organization = yes\n'
    legacy_org+=v('APDC_cooperation_container_law_selected_options^25',2)+v('APDC_cooperation_container_law_group_locks^25',1)+v('APDC_cooperation_container_law_option_2_available^25',0)+v('qa_legacy_tab_first','APDC_cooperation_container_law_tab_4_groups^0')
    legacy_org+='clr_country_flag = apdc_native_organization_rules_v1\nclear_array = apdc_nr_natives\nclear_array = apdc_nr_names\n'+''.join(f'clear_array = apdc_nr_override_{i}\n' for i in range(1,5))+v('apdc_nr_id',25,True)+'apdc_nr_ensure = yes\n'
    legacy_org+=check_reload('legacy_rule_adoption_keeps_choice_lock_and_availability',cv('APDC_cooperation_container_law_selected_options^25',2)+' '+cv('APDC_cooperation_container_law_group_locks^25',1)+' '+cv('APDC_cooperation_container_law_option_2_available^25',0))
    legacy_org+=check_reload('legacy_rule_adoption_restores_names_without_reordering',cv('apdc_nr_names^25','token:APDC_COOPERATION_LAW_GROUP_25')+' '+cv('APDC_cooperation_container_law_tab_4_groups^0','qa_legacy_tab_first')+' '+cv('apdc_nr_id',25)+' '+cv('apdc_nr_ensure_inputs^num',0))
    legacy_org+='APDC_remove_cooperation_organization = yes\n'
    body+=b('ITA',legacy_org)
    body+='clr_country_flag = apdc_native_cold_war_v1\napdc_parl_refresh_candidates = yes\napdc_na_refresh_all = yes\n'
    body+=check_reload('loaded_actual_saved_role_and_effect',cv('apdc_parl_role_7',2002)+' '+cv('qa_content_chief_balance',1))
    body+=v('qa_content_old_name_token',old_name,True)+check_reload('adding_token_file_reordered_saved_name_index','NOT = { '+cv('qa_content_old_name_token','token:qa_content_candidate')+' }')
    body+=check_reload('saved_role_name_rebound_from_permanent_id',cv('apdc_nc_role_name_7','token:qa_content_candidate')+' '+cv('APDC_prime_minister_character','token:GER_APDC_romy_riefenstahl'))
    body+=v('apdc_cw_id',1003)+v('apdc_cw_target','GER')+'apdc_cw_find_law = yes\n'
    body+=check_reload('saved_domestic_action_keeps_running',cv('apdc_cw_law_running^apdc_cw_law_index',1)+' '+cv('apdc_na_names^apdc_cw_law_index','token:qa_content_action'))
    body+=b('SOV','apdc_nr_refresh_rules = yes\nAPDC_sync_cooperation_organization_all_member_views = yes\n'+check_reload('saved_rule_choice_and_callbacks_are_preserved',cv('APDC_cooperation_container_law_selected_options^101',2)+' '+cv('qa_content_rule_enact',2)+' '+cv('qa_content_rule_repeal',1)))
    body+=check_reload('saved_member_effect_not_applied_twice',cv('qa_content_rule_member_balance',1)+' '+cv('apdc_nr_view_names^101','token:qa_content_rule'))
    body+=v('qa_content_roster_before_late','apdc_nc_ids^num')+v('apdc_nc_id',2003,True)+'apdc_register_candidate = yes\n'+v('qa_content_roster_after_expected','qa_content_roster_before_late')+'add_to_variable = { qa_content_roster_after_expected = 1 }\n'
    body+=check_reload('new_candidate_registers_without_core_rebuild',cv('apdc_nc_ids^num','qa_content_roster_after_expected'))
    body+=v('apdc_nc_id',2003,True)+v('apdc_parl_selected_role',8)+v('apdc_parl_free_deputy',1)+'apdc_appoint_candidate = yes\n'
    body+=check_reload('new_candidate_callback_and_identity_are_independent',cv('apdc_parl_role_8',2003)+' '+cv('apdc_parl_role_7',0)+' '+cv('qa_added_chief_balance',1)+' '+cv('qa_content_chief_balance',0))
    body+='log = "APDC_CONTENT_RELOAD NEW_CANDIDATE_NAME [APDCDeputyPrimeMinisterName]"\n'
    body+=b('for_loop_effect','start = 1 end = apdc_nc_ids^num value = qa_content_card_row\n'+b('if','limit = { '+cv('apdc_nc_ids^qa_content_card_row',2003)+' }\n'+v('apdc_parl_candidate_context','qa_content_card_row',True)))+'log = "APDC_CONTENT_RELOAD NEW_CANDIDATE_CARD [ApdcParlCandidateName]"\n'
    body+='set_country_flag = apdc_parl_open\n'+v('apdc_nc_id',2003,True)+'apdc_unregister_candidate = yes\n'
    body+=check_reload('withdrawing_candidate_refreshes_pool_and_preserves_office',cv('apdc_nc_ids^num','qa_content_roster_before_late')+' '+cv('apdc_parl_role_8',2003)+' '+cv('qa_added_chief_balance',1))
    body+=v('apdc_nc_id',2003,True)+'apdc_appoint_candidate = yes\napdc_parl_clear_role_8 = yes\nclr_country_flag = apdc_parl_open\n'
    body+=check_reload('withdrawn_candidate_cannot_reappoint_and_can_be_dismissed',cv('qa_added_chief_balance',0)+' '+cv('apdc_parl_role_8',0))
    body+=v('apdc_na_id',1004,True)+'apdc_unlock_cold_war_action = yes\n'+v('apdc_na_id',1004,True)+v('apdc_cw_target','FRA')+'apdc_execute_cold_war_action = yes\n'
    body+=check_reload('new_action_calls_its_own_execute_callback',cv('qa_added_action_execute',1)+' '+cv('apdc_cw_law_running^apdc_cw_law_row',1))
    body+=v('qa_added_action_row','apdc_cw_law_row')+'apdc_cw_tick_laws = yes\n'+v('apdc_cw_selected','FRA')+v('apdc_cw_tab',2)+'apdc_cw_refresh_view = yes\n'
    body+=check_reload('new_action_is_in_dynamic_list_and_sources','is_in_array = { array = apdc_cw_visible_laws value = var:qa_added_action_row } '+cv('apdc_na_names^qa_added_action_row','token:qa_added_action')+' '+cv('apdc_na_source_names^0','token:qa_added_action'))
    body+='log = "APDC_CONTENT_RELOAD NEW_ACTION_NAME [APDCCWLawName]"\nlog = "APDC_CONTENT_RELOAD NEW_ACTION_DESCRIPTION [APDCCWLawDescription]"\n'
    body+=v('apdc_na_id',1004,True)+v('apdc_cw_target','FRA')+'apdc_stop_cold_war_action = yes\n'+check_reload('new_action_calls_its_own_stop_callback',cv('qa_added_action_stop',1))
    body+=b('SOV',v('apdc_nr_id',102,True)+'apdc_register_organization_rule = yes\napdc_register_organization_rule = yes\n'+check_reload('new_rule_registers_without_resetting_old_choice',cv('APDC_cooperation_container_law_selected_options^102',1)+' '+cv('APDC_cooperation_container_law_selected_options^101',2)+' '+cv('qa_added_rule_enact',1)))
    body+=v('APDC_cooperation_law_group_id',102)+'log = "APDC_CONTENT_RELOAD NEW_RULE_NAME [APDCCooperationLawGroupName]"\n'
    body+='log = "APDC_CONTENT_RELOAD NEW_RULE_OPTION [APDCCooperationLawOption2Name]"\nlog = "APDC_CONTENT_RELOAD NEW_RULE_EFFECT [APDCCooperationLawOption2Effect]"\n'
    # Exercise actual public submission, queue, ballot and daily resolution.
    body+=b('SOV',v('APDC_cooperation_container_vote_state',2)+v('APDC_cooperation_container_vote_days_remaining',1))
    body+=v('apdc_nr_id',101,True)+v('apdc_nr_option',1,True)+'apdc_propose_organization_rule = yes\n'
    body+=b('SOV',check_reload('public_rule_proposal_uses_the_existing_queue',cv('APDC_cooperation_container_law_queue_groups^num',1)+' '+cv('APDC_cooperation_container_law_queue_groups^0',101)))
    body+=v('APDC_cooperation_queue_group_id',101)+v('APDC_cooperation_queue_index',0)+'log = "APDC_CONTENT_RELOAD QUEUED_RULE_NAME [APDCCooperationQueueLawGroupName]"\n'
    body+='log = "APDC_CONTENT_RELOAD QUEUED_RULE_OPTION [APDCCooperationQueueLawOptionName]"\n'
    body+=b('SOV','APDC_cooperation_legislation_daily_tick_container = yes\n'+check_reload('queued_rule_starts_normal_ballot',cv('APDC_cooperation_container_active_law_group',101)+' '+cv('APDC_cooperation_container_active_law_option',1)))
    body+='log = "APDC_CONTENT_RELOAD ACTIVE_RULE_NAME [APDCCooperationActiveLawGroupName]"\nlog = "APDC_CONTENT_RELOAD ACTIVE_RULE_OPTION [APDCCooperationActiveLawOptionName]"\nlog = "APDC_CONTENT_RELOAD ACTIVE_RULE_EFFECT [APDCCooperationActiveLawEffect]"\n'
    body+='APDC_cast_cooperation_vote_support = yes\n'
    body+=b('SOV',v('APDC_cooperation_container_vote_days_remaining',1)+'APDC_cooperation_legislation_daily_tick_container = yes\n'+check_reload('normal_ballot_resolves_to_native_rule_effects',cv('APDC_cooperation_container_law_selected_options^101',1)+' '+cv('qa_content_rule_enact',3)+' '+cv('qa_content_rule_repeal',2)))
    body+=check_reload('both_old_and_new_member_effects_stay_balanced',cv('qa_content_rule_member_balance',1)+' '+cv('qa_added_rule_member_balance',1))
    body+=v('apdc_parl_candidate_context',-1,True)+'log = "APDC_CONTENT_RELOAD HEADER_PORTRAIT [ApdcParlCandidatePortrait]"\n'
    body+=v('apdc_cw_law_row',-1,True)+'log = "APDC_CONTENT_RELOAD EMPTY_ACTION [APDCCWLawName] EMPTY_ACTION_END"\n'
    body+=v('APDC_cooperation_law_group_id',0,True)+'log = "APDC_CONTENT_RELOAD INACTIVE_RULE [APDCCooperationLawGroupName] INACTIVE_RULE_END"\n'
    body+='set_country_flag = qa_content_reload_done\nlog = "APDC_CONTENT_RELOAD END"\n'
    put(driver/'common/scripted_effects/AAA_native_reload_tests.txt',b('qa_native_content_reload',body))
    startup=b('if','limit = { has_country_flag = qa_content_initial_done }\nset_country_flag = qa_content_reload_enabled')
    # on_startup does not re-run for this saved game; the first daily pulse
    # after loading is the reliable, screen-independent regression entry.
    daily=b('if','limit = { has_country_flag = qa_content_initial_done NOT = { has_country_flag = qa_content_reload_done } }\nqa_native_content_reload = yes')
    put(driver/'common/on_actions/AAA_native_content_after_save.txt',b('on_actions',b('on_startup',b('effect',b('GER',startup)))+b('on_daily_GER',b('effect',daily))))
    continue_data=json.loads((profile/'continue_game.json').read_text('utf-8-sig'));continue_data['filename']=snapshot.name
    put(profile/'continue_game.json',json.dumps(continue_data,ensure_ascii=False,indent=2))
    runtime_dirs=['common/scripted_effects','common/scripted_triggers','common/scripted_guis','common/scripted_localisation','common/synchronized_dynamic_tokens','common/on_actions','interface','localisation/simp_chinese']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in runtime_dirs for p in (ROOT/folder).glob('*') if p.is_file()}
    plan=json.loads((REPORT/'qa-plan.json').read_text('utf-8'));plan.update({'reload_expected_checks':re.findall(r'APDC_CONTENT_RELOAD PASS (\w+)',body),'source_save':str(snapshot),'source_save_date':re.search(r'\bdate="([^"]+)"',saved)[1],'source_save_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'saved_candidate_name_token':old_name,'core_sha256_before_late_load':hashes})
    put(REPORT/'qa-plan.json',json.dumps(plan,ensure_ascii=False,indent=2));print(json.dumps({'saved_game':str(snapshot),'date':plan['source_save_date'],'new_independent_providers':3,'legacy_migration_probe_provider':1,'expected_reload_checks':len(plan['reload_expected_checks']),'core_files_fingerprinted':len(hashes)},ensure_ascii=False))

def check_reload(name,test):
    return check(name,test).replace('APDC_CONTENT_QA','APDC_CONTENT_RELOAD')

def verify_reload(profile):
    plan=json.loads((REPORT/'qa-plan.json').read_text('utf-8'));log=(profile/'logs/game.log').read_text('utf-8-sig',errors='replace');errors=(profile/'logs/error.log').read_text('utf-8-sig',errors='replace')
    passed=set(re.findall(r'APDC_CONTENT_RELOAD PASS (\w+)',log));failed=re.findall(r'APDC_CONTENT_RELOAD FAIL (\w+)',log);missing=sorted(set(plan['reload_expected_checks'])-passed)
    labels={'new_candidate_name':'NEW_CANDIDATE_NAME 读档新增候选人','new_rule_name':'NEW_RULE_NAME 读档新增组织规则','queue_name':'QUEUED_RULE_NAME 独立组织规则','header_portrait_fallback':'HEADER_PORTRAIT GFX_apdc_parl_empty_slot'}
    labels.update({'candidate_card':'NEW_CANDIDATE_CARD 读档新增候选人','action_name':'NEW_ACTION_NAME 读档新增冷战行动','action_description':'NEW_ACTION_DESCRIPTION 无须重建的新增内容','rule_option':'NEW_RULE_OPTION 新增选项二','rule_effect':'NEW_RULE_EFFECT 新增效果二','queue_option':'QUEUED_RULE_OPTION 规则选项一','active_rule':'ACTIVE_RULE_NAME 独立组织规则','active_option':'ACTIVE_RULE_OPTION 规则选项一','active_effect':'ACTIVE_RULE_EFFECT 选项一效果'})
    for label,text in labels.items():
        if text not in log:failed.append(label+'_localizes')
    for label in ['EMPTY_ACTION','INACTIVE_RULE']:
        if not re.search(label+r'\s+'+label+r'_END',log):failed.append(label.lower()+'_is_empty')
    related=[x for x in errors.splitlines() if any(k.lower() in x.lower() for k in ['apdc_nc','apdc_na_','apdc_nr_','apdc_candidate','apdc_cooperation_rule','apdc_cw_action','qa_content','qa_added','native_reload'])]
    changed=[p for p,h in plan['core_sha256_before_late_load'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if changed:failed.append('core_files_unchanged_after_late_content')
    out={'status':'passed' if not failed+missing+related else 'failed','passed':sorted(passed),'failed':failed,'missing':missing,'related_errors':related,'core_changed':changed,'source_save_date':plan['source_save_date'],'source_save_sha256':plan['source_save_sha256']}
    put(REPORT/'reload-runtime.json',json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False));return out['status']=='passed'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','verify','late-content','verify-reload']);p.add_argument('--profile',type=Path,default=PROFILE);a=p.parse_args()
    if a.action=='prepare':prepare(a.profile)
    elif a.action=='late-content':late_content(a.profile)
    elif a.action=='verify-reload':
        if not verify_reload(a.profile):raise SystemExit(1)
    elif not verify(a.profile):raise SystemExit(1)
