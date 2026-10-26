"""Create an isolated runtime fixture using the actual generated UI callbacks."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

from common import ROOT, WORK, parse, block


def build(output=None):
    sys.path.insert(0, str(ROOT / 'tools/performance'))
    import prepare_runtime
    qa = Path('D:/APDC_EconomyPanelQA_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    assert not qa.exists()
    prepare_runtime.QA = qa
    prepare_runtime.prepare(toolpack=True)
    (qa / 'driver/common/defines/zzzz_APDC_performance_qa.lua').write_text(
        'NDefines.NGame.GAME_SPEED_SECONDS = { 1.5, 1.5, 1.5, 1.5, 0.0 }\n', 'utf-8')
    scripted = parse((ROOT / 'common/scripted_guis/APDC_economy_panel_ui.txt').read_text('utf-8'))[0]
    callbacks = {}
    enabled = {}
    raw = (ROOT / 'common/scripted_guis/APDC_economy_panel_ui.txt').read_text('utf-8')
    for gui in scripted.children:
        triggers = gui.get('triggers')
        if triggers:
            for trigger in triggers.children:
                enabled[trigger.key] = raw[trigger.value_start + 1:trigger.value_end - 1]
        effects = gui.get('effects')
        if effects:
            for effect in effects.children:
                callbacks[effect.key] = raw[effect.value_start + 1:effect.value_end - 1]
    pieces = []
    installed = set()

    def click(name):
        key = 'APDC_eco_' + name + '_click'
        if name not in installed:
            pieces.append(block('QA_click_' + name, callbacks[key]))
            installed.add(name)
        return 'QA_click_' + name + ' = yes\n'

    def assertion(name, condition):
        return 'if = { limit = { ' + condition + ' } log = "APDC_PANEL_ASSERT PASS ' + name + '" } else = { log = "APDC_PANEL_ASSERT FAIL ' + name + '" }\n'

    coefficients = {'undisturbed_isolation': 1, 'isolation': 1, 'civilian_economy': 1,
                    'low_economic_mobilisation': .85, 'partial_economic_mobilisation': .7,
                    'war_economy': .55, 'tot_economic_mobilisation': .4}
    body = '''APDC_eco_refresh_current_supply = yes
log = "APDC_PANEL_INITIAL public=[?APDC_eco_public_civ] available=[?APDC_eco_public_available] native_total=[?num_of_civilian_factories] native_available=[?num_of_civilian_factories_available_for_projects] native_available_civ=[?num_of_available_civilian_factories] goods=[?APDC_eco_goods_per_civ_m] demand=[?APDC_eco_demand_m] private=[?APDC_eco_private_civ]"
'''
    body += assertion('initial_public_capacity_positive','check_variable = { APDC_eco_public_available > 0 }')
    body += assertion('initial_public_allocation_positive','check_variable = { APDC_eco_public_civ > 0 } NOT = { has_country_flag = APDC_eco_initial_public_allocation_pending }')
    body += 'set_variable = { APDC_eco_public_civ = 0 } APDC_eco_refresh_current_supply = yes\n'
    for name, target in [('public_plus', 1), ('public_minus', 0)]:
        condition = enabled['APDC_eco_' + name + '_click_enabled']
        body += assertion(name + '_enabled', condition)
        body += 'if = { limit = { ' + condition + ' } ' + click(name) + ' }\n'
        body += assertion(name + '_applies', 'check_variable = { APDC_eco_public_civ = ' + str(target) + ' }')
    laws_raw = (ROOT / 'common/ideas/APDC_economy_laws.txt').read_text('utf-8')
    laws = parse(laws_raw)[0]
    for slot,trait in [('city_idea','science_idea'),('society_development_idea','society_idea'),('poverty_level_idea','poverty_idea')]:
        body += assertion(slot+'_five_listed','has_allowed_idea_with_traits = { idea = '+trait+' limit = 4 characters = no }')
        for idea in laws.get(slot).children:
            if idea.value is not None:
                continue
            node = idea.get('available')
            condition = laws_raw[node.value_start + 1:node.value_end - 1]
            body += 'if = { limit = { has_idea = ' + idea.key + ' } ' + assertion(idea.key+'_current_available',condition) + ' } else = { ' + assertion(idea.key+'_alternative_locked','NOT = { '+condition+' }') + ' }\n'
    for law, value in coefficients.items():
        body += ''.join('remove_ideas = ' + key + '\n' for key in coefficients)
        body += 'add_ideas = ' + law + '\n'
        body += 'APDC_eco_refresh_policies = yes\n'
        body += assertion(law + '_coefficient', 'check_variable = { APDC_eco_population_base = ' + str(value) + ' }')
        body += 'set_temp_variable = { QA_native_cg_expected = modifier@consumer_goods_expected_value }\n'
        body += assertion(law + '_native_expected_suppressed', 'check_variable = { QA_native_cg_expected = -1 }')
    body += ''.join('remove_ideas = ' + key + '\n' for key in coefficients) + 'add_ideas = civilian_economy\n'
    item = next(e for e in json.loads((WORK / 'equipment_catalogue.json').read_text('utf-8')) if e['id'] == 'infantry_equipment_0')
    idx = item['index']
    body += 'set_technology = { infantry_weapons = 1 popup = no }\nAPDC_eco_refresh_equipment = yes\n'
    body += f'set_variable = {{ APDC_eco_stocks^{idx} = 20 }}\nset_temp_variable = {{ APDC_eco_equipment_id = {idx} }}\n'
    body += 'set_variable = { APDC_eco_cash_m = 10 } set_variable = { APDC_eco_cash_k = 0 } set_variable = { APDC_eco_panel_open = 1 }\n'
    body += click('eq_buy') + assertion('equipment_row_opens_purchase', 'check_variable = { APDC_eco_purchase_open = 1 } check_variable = { APDC_eco_purchase_quantity = 1 }')
    body += click('qty_add_10') + assertion('quantity_add_10', 'check_variable = { APDC_eco_purchase_quantity = 11 }')
    body += click('qty_remove_1') + assertion('quantity_remove_1', 'check_variable = { APDC_eco_purchase_quantity = 10 }')
    body += click('qty_max') + assertion('quantity_max', 'check_variable = { APDC_eco_purchase_quantity = 20 }')
    body += click('purchase_accept') + assertion('accept_buys_and_deducts', f'check_variable = {{ APDC_eco_stocks^{idx} = 0 }} check_variable = {{ APDC_eco_cash_m = 9 }} check_variable = {{ APDC_eco_cash_k = 998.28 }}')
    body += f'set_variable = {{ APDC_eco_stocks^{idx} = 5 }} set_variable = {{ APDC_eco_cash_m = 0 }} set_variable = {{ APDC_eco_cash_k = 0 }}\n'
    body += click('eq_buy') + click('purchase_accept') + assertion('cannot_buy_without_money', f'check_variable = {{ APDC_eco_stocks^{idx} = 5 }}')
    body += click('purchase_close') + assertion('purchase_close', 'NOT = { has_variable = APDC_eco_purchase_open }')
    body += click('trade_toggle') + assertion('trade_expand_frame_2', 'has_variable = APDC_eco_trade_open check_variable = { APDC_eco_trade_toggle_frame = 2 }')
    body += click('trade_toggle') + assertion('trade_collapse_frame_1', 'NOT = { has_variable = APDC_eco_trade_open } check_variable = { APDC_eco_trade_toggle_frame = 1 }')
    body += click('tax_law') + assertion('law_group_opens', 'check_variable = { APDC_eco_selected_group = 1 }')
    body += 'set_variable = { APDC_eco_cash_m = 1 } set_temp_variable = { APDC_eco_law_level = 3 }\n'
    body += assertion('current_row_highlight', enabled['APDC_eco_law_current_visible'])
    body += assertion('current_icon_coloured', enabled['APDC_eco_law_icon_click_enabled'])
    body += click('law_icon') + assertion('current_icon_no_charge_or_close','has_idea = APDC_eco_tax_3 check_variable = { APDC_eco_selected_group = 1 }')
    body += 'set_temp_variable = { APDC_eco_law_level = 2 } set_temp_variable = { QA_remove_pp = political_power } multiply_temp_variable = { QA_remove_pp = -1 } add_political_power = QA_remove_pp add_political_power = 149\n'
    body += assertion('insufficient_pp_disables_row','NOT = { '+enabled['APDC_eco_law_button_click_enabled']+' }')
    body += assertion('insufficient_pp_disables_icon','NOT = { '+enabled['APDC_eco_law_icon_click_enabled']+' }')
    body += click('law_icon') + assertion('disabled_law_click_cannot_apply','has_idea = APDC_eco_tax_3 check_variable = { APDC_eco_selected_group = 1 }')
    body += 'set_variable = { APDC_eco_cash_m = 1 } add_political_power = 1000 set_temp_variable = { APDC_eco_law_level = 2 }\n'
    body += assertion('affordable_law_enabled', enabled['APDC_eco_law_icon_click_enabled'])
    body += click('law_button') + assertion('selected_law_closes_sidebar', 'has_idea = APDC_eco_tax_2 NOT = { has_variable = APDC_eco_selected_group }')
    body += click('tax_law') + click('law_close') + assertion('manual_close_sidebar', 'NOT = { has_variable = APDC_eco_selected_group }')
    body += click('back') + assertion('panel_back_closes_children', 'NOT = { has_variable = APDC_eco_panel_open } NOT = { has_variable = APDC_eco_selected_group } NOT = { has_variable = APDC_eco_purchase_open } NOT = { has_variable = APDC_eco_trade_open }')
    # Exercise all three GUI instances in the actual renderer after callbacks.
    body += f'set_variable = {{ APDC_eco_purchase_id = {idx} }} set_variable = {{ APDC_eco_purchase_quantity = 1 }} set_variable = {{ APDC_eco_panel_open = 1 }} set_variable = {{ APDC_eco_purchase_open = 1 }} set_variable = {{ APDC_eco_selected_group = 1 }} set_variable = {{ APDC_eco_trade_open = 1 }} APDC_eco_prepare_purchase = yes APDC_eco_sync_ui = yes\n'
    body += assertion('distribution_speed_display', 'NOT = { check_variable = { APDC_eco_ui_distribution_speed > 0 } } NOT = { check_variable = { APDC_eco_ui_distribution_speed < -0.2 } }')
    body += 'set_temp_variable = { QA_distribution_expected = APDC_eco_ui_distribution_speed } add_to_temp_variable = { QA_distribution_expected = 0.8 } add_to_temp_variable = { QA_distribution_expected = APDC_eco_ui_distribution_bonus } clamp_temp_variable = { var = QA_distribution_expected min = 0 max = 1 }\n'
    body += assertion('distribution_sources_reproduce_actual_result', 'check_variable = { QA_distribution_expected = APDC_eco_distribution }')
    body += 'set_temp_variable = { APDC_eco_law_level = 2 }\n'
    body += 'log = "APDC_TOOLTIP_LAW [APDCEconomyLawTooltip]"\n'
    body += 'log = "APDC_TOOLTIP_ACTIVE [APDCEconomyActiveTaxTooltip]"\n'
    body += 'log = "APDC_TOOLTIP_DISTRIBUTION [APDCEconomyDistributionTooltip]"\n'
    body += 'log = "APDC_TOOLTIP_CONSTRUCTION [APDCEconomyCivBuildTooltip]"\n'
    pieces.append(block('QA_panel_fixtures', body))
    folder = qa / 'driver/common/scripted_effects'
    folder.mkdir(parents=True)
    (folder / 'APDC_panel_qa.txt').write_text(''.join(pieces), 'utf-8')
    on = 'on_actions = { on_daily_GER = { effect = { if = { limit = { NOT = { has_country_flag = QA_panel_tested } } set_country_flag = QA_panel_tested QA_panel_fixtures = yes } if = { limit = { date > 2060.1.2 NOT = { has_country_flag = QA_panel_rendered } } set_country_flag = QA_panel_rendered QA_click_back = yes } log = "APDC_PANEL_DAY date=[GetDateText]" } } }\n'
    (qa / 'driver/common/on_actions/zzzz_APDC_performance_qa.txt').write_text(on, 'utf-8')
    out = output or ROOT / 'docs/economy/20261023-panel-regressions'
    out.mkdir(parents=True,exist_ok=True)
    (out / 'qa-profile.txt').write_text(str(qa), 'utf-8')
    userdir = Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
    files = [userdir / n for n in ['dlc_load.json', 'settings.txt', 'continue_game.json', 'save games/autosave.hoi4']]
    (out / 'user-files-before.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}, indent=2), 'utf-8')
    print(qa)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    build(parser.parse_args().output)
