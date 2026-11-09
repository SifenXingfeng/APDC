"""Prepare one isolated GER fixture; launching is a separate explicit step."""
from common import *
import re

PROFILE=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_20261107')


def assertion(test,label):
    return iff(test,'log = "APDC_PARL_QA PASS '+label+'"\n','log = "APDC_PARL_QA FAIL '+label+'"\n')


def prepare():
    PROFILE.mkdir(parents=True,exist_ok=True)
    driver=PROFILE/'driver'
    for folder in ['common/on_actions','common/defines','common/scripted_effects','common/ideas','common/synchronized_dynamic_tokens','localisation/simp_chinese','interface']:
        (driver/folder).mkdir(parents=True,exist_ok=True)
    (PROFILE/'mod').mkdir(exist_ok=True)
    descriptor=read('descriptor.mod')
    descriptor=re.sub(r'^path=.*$', 'path="'+ROOT.as_posix()+'"',descriptor,flags=re.M)
    (PROFILE/'mod/APDC.mod').write_text(descriptor,encoding='utf-8')
    (PROFILE/'mod/APDC_ParliamentQA.mod').write_text('name="APDC parliament validation"\npath="'+driver.as_posix()+'"\ndependencies={ "少女前线-APDC" }\nsupported_version="1.19.*"\n',encoding='utf-8')
    user_dlc=ROOT.parent.parent/'dlc_load.json'
    disabled=json.loads(user_dlc.read_text('utf-8-sig')).get('disabled_dlcs',[]) if user_dlc.exists() else []
    (PROFILE/'dlc_load.json').write_text(json.dumps({'enabled_mods':['mod/APDC.mod','mod/APDC_ParliamentQA.mod'],'disabled_dlcs':disabled}),encoding='utf-8')
    (PROFILE/'settings.txt').write_text('language="l_simp_chinese"\ngraphics={ size={ x=1920 y=1080 } min_gui={ x=1280 y=720 } gui_scale=1.0 fullScreen=no borderless=no shadows=no multi_sampling=0 maxanisotropy=0 vsync=no }\nmaster_volume=0\nmusic_volume=0\nsound_fx_volume=0\nsave_as_binary=no\nautosave="MONTHLY"\n',encoding='utf-8')
    # 1.19 reads display mode/resolution from this newer settings file.
    (PROFILE/'pdx_settings.txt').write_text('"Graphics"={ "display_mode"={ value="windowed" version=0 } "windowed_resolution"={ value="1920x1080" version=0 } "fullscreen_resolution"={ value="1920x1080" version=0 } "renderer"={ value="dx11" version=0 } "vsync"={ enabled=no version=0 } }\n"System"={ "language"={ value="l_simp_chinese" version=0 } }\n',encoding='utf-8')
    (driver/'common/defines/zzzz_apdc_parl_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.05, 0.05, 0.05, 0.05, 0.0 }\n',encoding='utf-8')
    # Keep native dimensions. Ancestor scaling is unreliable for gridboxes;
    # launch with -NormalGraphics to retain the profile's 1920x1080 window.
    gui=read('interface/apdc_parliament.gui')
    (driver/'interface/apdc_parliament.gui').write_text(gui,encoding='utf-8')
    (driver/'interface/apdc_parl_qa_list.gui').write_text('guiTypes = {}\n',encoding='utf-8')
    (driver/'common/scripted_guis').mkdir(exist_ok=True)
    (driver/'common/scripted_guis/apdc_parl_qa_list.txt').write_text('scripted_gui = {}\n',encoding='utf-8')
    # A separate QA idea supplies ordinary speed without altering source laws.
    (driver/'common/ideas/apdc_parliament_qa.txt').write_text(block('ideas',block('hidden_ideas',block('apdc_parl_qa_weight',block('modifier',P+'communism_seat_factor = 0.1'))+block('apdc_parl_qa_speed',block('modifier',P+'review_speed_factor = 2'))+block('apdc_parl_qa_zero',block('modifier','\n'.join(P+p+'_seat_factor = -1' for p in PARTIES))))),encoding='utf-8')
    (driver/'common/synchronized_dynamic_tokens/apdc_parl_qa.txt').write_text('apdc_parl_qa_special_name\napdc_parl_qa_special_desc\n',encoding='utf-8')
    (driver/'localisation/simp_chinese/apdc_parl_qa_l_simp_chinese.yml').write_text('l_simp_chinese:\n apdc_parl_qa_special_name:0 "验证议案"\n apdc_parl_qa_special_desc:0 "验证特殊议案接口"\n',encoding='utf-8-sig')
    hook=effect('special_passed_hook','set_country_flag = apdc_parl_qa_special_passed\n')+effect('special_failed_hook','set_country_flag = apdc_parl_qa_special_failed\n')+effect('special_submitted_hook','set_country_flag = apdc_parl_qa_special_submitted\n')
    (driver/'common/scripted_effects/apdc_parliament_story_hooks.txt').write_text(hook,encoding='utf-8')
    start='log = "APDC_PARL_QA START [GetDateText] date=[?global.date] next=[?apdc_parl_next_date.GetDateStringNoHour] days=[?days_until_next_election]"\n'
    start+=assertion('has_country_flag = apdc_parl_initialized '+ck('seat_total','=',500),'initial_500')
    start+=assertion(ck('seats_socialism','=',200)+' '+ck('seats_social_democracy','=',50)+' '+ck('seats_conservatism','=',150),'initial_hamilton')
    start+=assertion(ck('support','=',84),'initial_party_attitudes')
    start+=assertion(ck('effective_socialism','=',.4)+' '+ck('effective_social_democracy','=',.09),'initial_party_bonuses')
    start+=sv('qa_initial_date','global.date')+'set_country_flag = apdc_parl_open\napdc_parl_initialize_ui_arrays = yes\n'+sv('qa_day',0)
    # Core fixtures run once, after normal initialization and the first date
    # tick. The final fixture is a valid in-progress bill for save and UI QA.
    core='set_political_power = 2000\nset_variable = { APDC_eco_cash_m = 1000 }\nset_variable = { APDC_eco_cash_k = 0 }\n'
    core+='add_ideas = apdc_parl_qa_zero\napdc_parl_allocate_seats = yes\n'+assertion('has_country_flag = apdc_parl_allocation_error '+ck('seats_socialism','=',200),'zero_weights_preserve_old_seats')+'remove_ideas = apdc_parl_qa_zero\napdc_parl_allocate_seats = yes\n'
    core+='set_popularities = { communism = 30 socialism = 70 }\n'+sv('qa_pop_before','party_popularity@communism')+'add_ideas = apdc_parl_qa_weight\napdc_parl_allocate_seats = yes\nlog = "APDC_PARL_QA WEIGHT seats=[?apdc_parl_seats_communism]/[?apdc_parl_seats_socialism] popular=[?party_popularity@communism] weight=[?apdc_parl_weight_communism]"\n'+assertion(ck('seats_communism','=',160)+' '+ck('seats_socialism','=',340)+' check_variable = { party_popularity@communism = apdc_parl_qa_pop_before }','seat_coefficient_changes_only_weight')+'remove_ideas = apdc_parl_qa_weight\n'
    core+='set_popularities = { communism = 50 socialism = 50 }\n'+''.join(sv('alliance_'+p,0) for p in PARTIES)+'apdc_parl_run_election = yes\n'
    core+='log = "APDC_PARL_QA TIE seats=[?apdc_parl_seats_communism]/[?apdc_parl_seats_socialism] ties=[?apdc_parl_winner_ties]"\n'+assertion('has_country_flag = apdc_parl_election_tied '+ck('seats_communism','=',250)+' '+ck('seats_socialism','=',250)+' has_government = socialism','tie_keeps_incumbent')
    core+='log = "APDC_PARL_QA TIE_CALENDAR pending=[?days_until_next_election]"\n'
    core+='set_popularities = { communism = 60 socialism = 40 }\napdc_parl_force_election = yes\n'
    core+=assertion('has_government = communism NOT = { has_country_flag = apdc_parl_election_tied } '+ck('free_prime','=',1)+' '+ck('free_deputy','=',1),'election_winner_and_free_formation')
    core+=sv('alliance_communism',1)+sv('alliance_conservatism',1)+sv('alliance_socialism',2)+sv('alliance_social_democracy',2)+'set_popularities = { communism = 30 socialism = 25 social_democracy = 20 liberalism = 15 conservatism = 10 }\napdc_parl_force_election = yes\n'+assertion('has_government = socialism has_country_flag = APDC_governing_coalition_socialism has_country_flag = APDC_governing_coalition_social_democracy NOT = { has_country_flag = APDC_governing_coalition_communism } '+ck('winner_ties','=',1),'electoral_alliance_plurality_counted_once')+''.join(sv('alliance_'+p,0) for p in PARTIES)+'set_popularities = { communism = 60 socialism = 40 }\napdc_parl_force_election = yes\n'
    core+='APDC_add_socialism_to_governing_coalition = yes\n'
    core+=assertion('apdc_parl_can_ban_communism = no apdc_parl_can_ban_socialism = no','protected_ruler_and_coalition')
    core+='APDC_remove_socialism_from_governing_coalition = yes\napdc_parl_finish_agenda = yes\nAPDC_update_cabinet_statistics = yes\napdc_parl_select_role = { ROLE = 1 }\napdc_parl_appoint_1 = yes\n'
    core+=assertion(ck('role_1','=',1)+' has_idea = GER_APDC_romy_riefenstahl','member_trait_applied')
    core+='apdc_parl_select_role = { ROLE = 7 }\napdc_parl_appoint_1 = yes\n'
    core+=assertion(ck('role_7','=',1)+' '+ck('role_1','=',0)+' '+ck('free_prime','=',0)+' '+ck('free_deputy','=',1)+' has_idea = apdc_parl_chief_1 NOT = { has_idea = GER_APDC_romy_riefenstahl }','one_person_one_role_and_trait_switch')
    # Population-free support exactly 50: every seat is socialist opposition,
    # whose base -10 is offset by a registered +10 story source.
    core+='apdc_parl_enact_political_system_4 = yes\n'+''.join(sv('seats_'+p,500 if p=='socialism' else 0) for p in PARTIES)
    core+='apdc_parl_set_socialism_attitude_source = { NAME = apdc_parl_source_story VALUE = 10 }\napdc_parl_refresh = yes\n'
    core+=assertion(ck('support','=',50),'support_exactly_50')
    core+='apdc_parl_submit_agenda = { KIND = 1 TARGET = 3 OPTION = 3 }\n'+sv('bill_work',80)+'apdc_parl_refresh = yes\napdc_parl_validate_agenda = yes\n'
    core+=assertion(ck('stage','=',3)+' '+ck('agenda','=',1),'50_enters_review')
    core+='apdc_parl_change_socialism_bill_attitude = { VALUE = -1 }\napdc_parl_validate_agenda = yes\n'
    core+=assertion(ck('agenda','=',0)+' '+ck('last_result','=',-1),'below_50_fails_review')
    # Clamp +75/+50 to 100 while separating bill attitudes from government.
    core+='apdc_parl_set_socialism_attitude_source = { NAME = apdc_parl_source_story VALUE = 85 }\napdc_parl_change_socialism_bill_attitude = { VALUE = 50 }\n'
    core+=assertion(ck('attitude_socialism','=',75)+' '+ck('bill_support_socialism','=',100),'bill_attitude_clamped_independently')
    core+='apdc_parl_finish_agenda = yes\napdc_parl_set_socialism_attitude_source = { NAME = apdc_parl_source_story VALUE = 10 }\napdc_parl_enact_political_system_6 = yes\nadd_ideas = apdc_parl_qa_speed\napdc_parl_submit_agenda = { KIND = 1 TARGET = 3 OPTION = 3 }\n'+sv('bill_work',45)+'apdc_parl_refresh = yes\n'
    core+=assertion(ck('progress','=',50)+' '+ck('remaining_days','=',15),'remaining_progress_not_retroactive')
    core+='apdc_parl_set_socialism_attitude_source = { NAME = apdc_parl_source_story VALUE = 100 }\n'+sv('seats_socialism',500)+'apdc_parl_refresh = yes\n'
    # Regime 6 caps S at125: attitude90 gives117.5, extra speed35%, total4.05.
    core+=assertion(ck('support','=',117.5)+' '+ck('support_speed','=',4.05),'support_speed_multiplies_ordinary_speed')
    core+=sv('qa_saved_work',var('bill_work'))+sv('qa_saved_attitude',var('bill_attitude_socialism'))+'apdc_parl_force_election = yes\n'
    core+=assertion(ck('bill_work','=',var('qa_saved_work'))+' '+ck('bill_attitude_socialism','=',var('qa_saved_attitude'))+' '+ck('agenda','=',1),'election_preserves_bill_and_attitudes')
    core+='remove_ideas = apdc_parl_qa_speed\napdc_parl_finish_agenda = yes\napdc_parl_clear_socialism_attitude_sources = yes\napdc_parl_enact_political_system_1 = yes\napdc_parl_submit_ban_socialism = yes\n'
    core+=assertion('has_country_flag = apdc_parl_banned_socialism '+ck('seats_socialism','=',0)+' '+ck('seats_communism','=',500),'instant_ban_forces_new_election')
    core+='apdc_parl_submit_unban_socialism = yes\n'
    core+=assertion('NOT = { has_country_flag = apdc_parl_banned_socialism } '+ck('seats_socialism','=',0),'unban_waits_for_next_election')
    core+='apdc_parl_force_election = yes\n'+assertion(ck('seats_socialism','=',200),'unbanned_party_returns_next_election')
    # Native economic ideas and real price calculation, including zero price.
    core+='APDC_set_economic_system_bandit_economy = yes\nAPDC_eco_initialize_stock_arrays = yes\nset_variable = { APDC_eco_stocks^1 = 10 }\nset_variable = { APDC_eco_purchase_id = 1 }\nset_variable = { APDC_eco_purchase_quantity = 1 }\nAPDC_eco_prepare_purchase = yes\n'
    core+=assertion('check_variable = { APDC_eco_purchase_unit_k = 0 } check_variable = { APDC_eco_purchase_cost_m = 0 } check_variable = { APDC_eco_purchase_cost_k = 0 }','minus_100_purchase_price_zero')
    core+='APDC_eco_purchase_equipment = yes\n'+assertion('check_variable = { APDC_eco_stocks^1 = 9 }','zero_price_purchase_delivers_and_consumes_stock')
    core+='APDC_set_economic_system_traditional_agriculture = yes\nAPDC_eco_prepare_purchase = yes\n'+assertion('check_variable = { APDC_eco_purchase_unit_k = 4.8 }','plus_200_purchase_price_triples')
    core+='64 = { add_building_construction = { type = APDC_eco_private_civ level = 1 instant_build = yes } }\nclr_country_flag = APDC_eco_statistics_today\nAPDC_eco_ensure_country_statistics = yes\n'+sv('qa_private_before','APDC_eco_private_civ_raw')+'APDC_set_economic_system_decentralized_planning = yes\nclr_country_flag = APDC_eco_statistics_today\nAPDC_eco_ensure_country_statistics = yes\n'
    core+=assertion('check_variable = { APDC_eco_private_civ_raw = '+var('qa_private_before')+' }','decentralized_keeps_private_industry')
    core+='APDC_set_economic_system_central_planning = yes\nclr_country_flag = APDC_eco_statistics_today\nAPDC_eco_ensure_country_statistics = yes\n'+assertion('check_variable = { APDC_eco_private_civ_raw = 0 } check_variable = { APDC_eco_private_mil_raw = 0 }','central_nationalizes_private_industry')
    core+='apdc_parl_register_special_bill = { ID = 900001 NAME = apdc_parl_qa_special_name DESC = apdc_parl_qa_special_desc COST = 0 }\n'+sv('selected_special_index',0)+'apdc_parl_submit_special_bill = yes\n'
    core+=assertion(ck('last_passed_special_id','=',900001)+' has_country_flag = apdc_parl_qa_special_passed has_country_flag = apdc_parl_qa_special_submitted','special_bill_callbacks')
    core+='apdc_parl_remove_special_bill = { ID = 900001 }\n'+assertion('check_variable = { apdc_parl_special_ids^num = 0 }','special_bill_removal')
    # Restore the normal GER party split and original scripted coalition for
    # screenshots and the monthly save. Political offices remain a test record.
    core+='apdc_parl_finish_agenda = yes\nset_popularities = { communism = 0 socialism = 40 social_democracy = 10 conservatism = 30 liberalism = 10 authoritarianism = 10 dictatorship = 0 fascism = 0 fundamentalism = 0 }\nset_politics = { ruling_party = socialism elections_allowed = yes election_frequency = 24 }\nAPDC_clear_governing_coalition = yes\nAPDC_add_socialism_to_governing_coalition = yes\nAPDC_add_social_democracy_to_governing_coalition = yes\napdc_parl_allocate_seats = yes\napdc_parl_enact_political_system_4 = yes\nAPDC_set_economic_system_market_socialism = yes\napdc_parl_enact_women_rights_3 = yes\napdc_parl_enact_relic_technology_3 = yes\napdc_parl_refresh = yes\nset_country_flag = apdc_parl_open\napdc_parl_submit_agenda = { KIND = 1 TARGET = 3 OPTION = 2 }\n'
    core+='clr_country_flag = apdc_parl_candidate_panel_open\n'+sv('selected_role',0)+'clear_variable = apdc_parl_selected_group\nlog = "APDC_PARL_QA CORE_FINISHED next=[?apdc_parl_next_date.GetDateStringNoHour]"\n'
    day=op('qa_day','add',1)
    split=core.index('set_popularities = { communism = 60 socialism = 40 }')
    prelude,remaining=core[:split],core[split:]
    day+=iff(ck('qa_day','=',1),sv('qa_date_delta','global.date')+op('qa_date_delta','subtract',var('qa_initial_date'))+'log = "APDC_PARL_QA DATE_DELTA [?apdc_parl_qa_date_delta]"\n'+prelude)
    day+=iff(ck('qa_day','=',2),'log = "APDC_PARL_QA TIE_CALENDAR after_tick=[?days_until_next_election]"\n'+assertion('check_variable = { days_until_next_election > 170 } check_variable = { days_until_next_election < 185 }','tie_calendar_six_months')+remaining)
    day+=iff(ck('qa_day','=',3),'log = "APDC_PARL_QA VISUAL main"\n')
    day+=iff(ck('qa_day','=',8),'apdc_parl_select_role = { ROLE = 1 }\nlog = "APDC_PARL_QA VISUAL cabinet"\n')
    day+=iff(ck('qa_day','=',13),'clr_country_flag = apdc_parl_candidate_panel_open\n'+sv('selected_group',5)+'apdc_parl_refresh_law_options = yes\nlog = "APDC_PARL_QA VISUAL law_side"\n')
    day+=iff(ck('qa_day','=',18),'clear_variable = apdc_parl_selected_group\nlog = "APDC_PARL_QA VISUAL main_return"\n')
    day+=iff(ck('qa_day','=',35),assertion(ck('seat_total','=',500),'monthly_state_survives')+'log = "APDC_PARL_QA COMPLETE day35"\n')
    actions='on_startup = { effect = { GER = { '+start+' } } }\non_daily_GER = { effect = { '+day+' } }\n'
    (driver/'common/on_actions/zzzzzz_apdc_parliament_qa.txt').write_text(lower_parameters(block('on_actions',actions)),encoding='utf-8')
    meta={'profile':str(PROFILE),'driver':str(driver),'project':str(ROOT),'enabled_mods':['APDC','APDC Parliament QA'],'disabled_dlcs':disabled,'user_settings_modified':False,'launch_required':True}
    (REPORT/'runtime-profile.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(meta,ensure_ascii=False))


if __name__=='__main__':
    import re
    prepare()
