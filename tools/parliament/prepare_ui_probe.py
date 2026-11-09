"""Prepare an isolated native GUI fixture for targeted window-message tests."""
from common import *
import runtime

PROFILE=Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_ui_20261107')


def main():
    runtime.PROFILE=PROFILE
    runtime.REPORT=ROOT/'docs/parliament/20261107-ui-corrections'
    runtime.prepare()
    driver=PROFILE/'driver'
    (driver/'common/defines/zzzz_apdc_parl_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.0 }\n',encoding='utf-8')
    start='set_political_power = 2000\nset_popularities = { communism = 60 socialism = 40 }\nset_politics = { ruling_party = communism elections_allowed = yes election_frequency = 24 }\nAPDC_clear_governing_coalition = yes\nAPDC_add_communism_to_governing_coalition = yes\nAPDC_add_socialism_to_governing_coalition = yes\n'
    start+=''.join(sv('winner_'+p,int(p in ('communism','socialism'))) for p in PARTIES)
    start+='apdc_parl_allocate_seats = yes\napdc_parl_finish_agenda = yes\nAPDC_update_cabinet_statistics = yes\napdc_parl_refresh = yes\nset_country_flag = apdc_parl_open\nclr_country_flag = apdc_parl_candidate_panel_open\nclear_variable = apdc_parl_selected_group\ncapital_scope = { goto_state = THIS }\n'
    start+='log = "APDC_UI READY date=[?apdc_parl_next_year]/[?apdc_parl_next_month]/[?apdc_parl_next_day]"\n'
    tick=sv('ui_candidate_open',0)+iff('has_country_flag = apdc_parl_candidate_panel_open',sv('ui_candidate_open',1))
    tick+=sv('ui_main_open',0)+iff('has_country_flag = apdc_parl_open',sv('ui_main_open',1))
    tick+='log = "APDC_UI STATE main=[?apdc_parl_ui_main_open] candidate=[?apdc_parl_ui_candidate_open] selected=[?apdc_parl_selected_role] slot1=[?apdc_parl_role_1] group=[?apdc_parl_selected_group] agenda=[?apdc_parl_agenda] y=[?apdc_parl_next_year] m=[?apdc_parl_next_month] d=[?apdc_parl_next_day]"\n'
    start+=sv('ui_probe_day',0)
    tick+=op('ui_probe_day','add',1)
    tick+=iff(ck('ui_probe_day','=',2),'log = "APDC_UI VISUAL main"\n')
    tick+=iff(ck('ui_probe_day','=',4),'apdc_parl_select_role = { ROLE = 1 }\napdc_parl_appoint_1 = yes\n'+runtime.assertion(ck('role_1','=',1)+' has_idea = GER_APDC_romy_riefenstahl','ui_member_appointed')+'log = "APDC_UI VISUAL cabinet_appointed"\n')
    tick+=iff(ck('ui_probe_day','=',7),'apdc_parl_dismiss_selected = yes\n'+runtime.assertion(ck('role_1','=',0)+' NOT = { has_idea = GER_APDC_romy_riefenstahl }','ui_dismiss_removes_role_and_bonus')+'log = "APDC_UI VISUAL cabinet_dismissed"\n')
    tick+=iff(ck('ui_probe_day','=',10),'clr_country_flag = apdc_parl_candidate_panel_open\n'+sv('selected_group',5)+'apdc_parl_refresh_law_options = yes\nlog = "APDC_UI VISUAL law_side"\n')
    tick+=iff(ck('ui_probe_day','=',13),'clear_variable = apdc_parl_selected_group\n'+op('dirty','add',1)+'log = "APDC_UI VISUAL folded"\n')
    tick+=iff(ck('ui_probe_day','=',16),'clr_country_flag = apdc_parl_open\nset_country_flag = apdc_ui_entry_preview\n'+op('dirty','add',1)+'log = "APDC_UI VISUAL entry_preview"\n')
    tick+=iff(ck('ui_probe_day','=',20),'log = "APDC_UI COMPLETE"\n')
    action='on_startup = { effect = { GER = { '+start+' } } }\non_daily_GER = { effect = { '+tick+' } }'
    (driver/'common/on_actions/zzzzzz_apdc_parliament_qa.txt').write_text(lower_parameters(block('on_actions',action)),encoding='utf-8')
    # Preview the actual political-page art and unchanged prime/deputy roles,
    # attaching the actual entry to the same y=44 art origin. This is a QA
    # composition, not a claim that the native politics tab was mouse-opened.
    gui=read('interface/apdc_parliament.gui')
    gui+='\n'
    frame='containerWindowType = { name = "apdc_ui_entry_preview" position = { x = 80 y = 120 } size = { width = 550 height = 636 } iconType = { name = "qa_art" position = { x = 0 y = 44 } spriteType = "GFX_pol_view_bg" alwaystransparent = yes } containerWindowType = { name = "apdc_ui_entry_hook" position = { x = 0 y = 0 } size = { width = 550 height = 636 } } }'
    (driver/'interface/apdc_ui_entry_preview.gui').write_text(block('guiTypes',frame),encoding='utf-8')
    sgui=read('common/scripted_guis/apdc_parliament.txt')
    sgui=sgui.replace('parent_window_token = politics_tab','parent_window_name = "apdc_ui_entry_hook"')
    roles=read('common/scripted_guis/APDC_cabinet_scripted_gui.txt').replace('parent_window_token = politics_tab','parent_window_name = "apdc_ui_entry_hook"')
    preview=block('apdc_ui_entry_preview','context_type = player_context window_name = "apdc_ui_entry_preview" visible = { has_country_flag = apdc_ui_entry_preview }')
    # Native parent-window lookup happens when the GUI is instantiated. Put
    # the preview parent, roles and all parliament children in that exact
    # order in one QA file, so none can fall back to the desktop root.
    combined=preview
    for source in [roles,sgui]:combined+='\n'.join(source[n.start:n.end] for outer in parse(source) for n in outer.children)
    (driver/'common/scripted_guis/APDC_cabinet_scripted_gui.txt').write_text(block('scripted_gui',combined),encoding='utf-8')
    (driver/'common/scripted_guis/apdc_parliament.txt').write_text('scripted_gui = {}\n',encoding='utf-8')
    (driver/'common/scripted_guis/apdc_ui_entry_preview.txt').write_text('scripted_gui = {}\n',encoding='utf-8')
    print(json.dumps({'profile':str(PROFILE),'status':'prepared'},ensure_ascii=False))


if __name__=='__main__':main()
