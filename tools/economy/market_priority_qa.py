"""Isolated native-engine checks for seller-side consumer trade priority."""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from common import ROOT, block, cond, parse, lower_math

OUT = ROOT / 'docs/economy/20261024-seller-priority'


def prepare():
    sys.path.insert(0, str(ROOT / 'tools/performance'))
    import prepare_runtime
    profile = Path('D:/APDC_MarketPriorityQA_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    assert not profile.exists()
    prepare_runtime.QA = profile
    prepare_runtime.prepare(toolpack=True)
    names = []

    def assertion(name, condition):
        assert name not in names, name
        names.append(name)
        return cond(condition, 'log = "APDC_PRIORITY PASS ' + name + '"', 'log = "APDC_PRIORITY FAIL ' + name + '"')

    def country(tag, **values):
        return tag + ' = {\n' + ''.join('set_variable = { APDC_eco_' + key + ' = ' + str(value) + ' }\n' for key, value in values.items()) + '}\n'

    def want(tag, variable, value, name):
        return tag + ' = { ' + assertion(name, 'check_variable = { APDC_eco_' + variable + ' = ' + str(value) + ' }') + ' }\n'

    def reset():
        return 'every_country = {\n' + ''.join('set_variable = { APDC_eco_' + key + ' = ' + str(value) + ' }\n' for key, value in {
            'import_target_m': 0, 'export_target_m': 0, 'domestic_m': 0, 'extra_input': 0, 'extra_output': 0,
            'demand_m': 0, 'distribution': 1, 'tariff': 0}.items()) + '}\n'

    def cycle(buffer=None):
        begin = 'APDC_eco_market_begin' + ('' if buffer is None else '_' + str(buffer))
        return begin + ' = yes\nfor_loop_effect = { start = 0 end = 7 value = QA_priority_drain APDC_eco_market_step = yes }\n'

    def conservation(name):
        return ('set_variable = { global.QA_priority_balance = 0 }\n'
                'every_country = { add_to_variable = { global.QA_priority_balance = APDC_eco_imports_m } subtract_from_variable = { global.QA_priority_balance = APDC_eco_exports_m } }\n' +
                assertion(name, 'check_variable = { global.QA_priority_balance > -0.0001 } check_variable = { global.QA_priority_balance < 0.0001 }'))

    body = ''
    for buffer in [0, 1]:
        prefix = 'buffer_' + str(buffer) + '_'
        body += reset() + country('GER', export_target_m=5, tariff=2.5)
        body += country('FRA', import_target_m=4, tariff=0, demand_m=10)
        body += country('ENG', import_target_m=10, tariff=1, demand_m=100)
        body += country('LLU', import_target_m=10, tariff=2.5, demand_m=1000)
        body += cycle(buffer)
        body += want('FRA', 'imports_m', 4, prefix + 'lowest_tariff_filled')
        body += want('ENG', 'imports_m', 1, prefix + 'second_tariff_gets_remainder')
        body += want('LLU', 'imports_m', 0, prefix + 'higher_tariff_waits_despite_larger_gap')
        body += want('GER', 'exports_m', 5, prefix + 'supply_cap')
        body += assertion(prefix + 'two_sequential_deals', 'check_variable = { global.APDC_eco_market_quantity_' + str(buffer) + '^num = 2 } check_variable = { global.APDC_eco_market_quantity_' + str(buffer) + '^0 = 4 } check_variable = { global.APDC_eco_market_quantity_' + str(buffer) + '^1 = 1 }')
        body += conservation(prefix + 'conservation')

        body += reset() + country('GER', export_target_m=5)
        body += country('FRA', import_target_m=2, tariff=1, demand_m=100)
        body += country('ENG', import_target_m=10, tariff=1, demand_m=50)
        body += country('LLU', import_target_m=10, tariff=1, demand_m=10)
        body += cycle(buffer)
        body += want('FRA', 'imports_m', 2, prefix + 'absolute_gap_beats_larger_import_quota')
        body += want('ENG', 'imports_m', 3, prefix + 'next_buyer_only_after_first_filled')
        body += want('LLU', 'imports_m', 0, prefix + 'smallest_gap_waits')

    body += reset() + country('GER', export_target_m=5)
    body += country('FRA', import_target_m=10, tariff=1, demand_m=100)
    body += country('ENG', import_target_m=1, tariff=1, demand_m=10)
    body += cycle()
    body += want('FRA', 'imports_m', 5, 'unfilled_first_buyer_receives_all_available_supply')
    body += want('ENG', 'imports_m', 0, 'no_equal_share_for_second_buyer')

    for large, small in [('ENG', 'FRA'), ('FRA', 'ENG')]:
        body += reset() + country('GER', export_target_m=.1)
        body += country(large, import_target_m=.1, tariff=1, demand_m=.4)
        body += country(small, import_target_m=.1, tariff=1, demand_m=.2) + cycle()
        body += want(large, 'imports_m', .1, large.lower() + '_fractional_gap_has_priority')
        body += want(small, 'imports_m', 0, small.lower() + '_smaller_fractional_gap_waits')

    body += reset() + country('GER', export_target_m=5)
    body += country('FRA', import_target_m=4, tariff=1, demand_m=1000, domestic_m=900, supply_m=9999)
    body += country('ENG', import_target_m=8, tariff=1, demand_m=10, supply_m=9999)
    body += cycle(0)
    body += want('FRA', 'imports_m', 4, 'absolute_shortage_beats_shortage_percentage')
    body += want('ENG', 'imports_m', 1, 'old_trade_supply_does_not_shrink_priority_gap')
    body += want('FRA', 'market_demand_score_0', 100, 'priority_uses_pre_trade_domestic_supply')

    body += reset() + country('GER', export_target_m=5)
    body += country('FRA', import_target_m=10, tariff=1, demand_m=100, domestic_m=100, extra_input=20, distribution=.5)
    body += country('ENG', import_target_m=10, tariff=1, demand_m=60, domestic_m=20, extra_output=10, distribution=.5)
    body += cycle(1)
    body += want('FRA', 'market_demand_score_1', 40, 'gap_includes_extra_input_and_distribution')
    body += want('ENG', 'market_demand_score_1', 55, 'gap_includes_extra_output_and_distribution')
    body += want('ENG', 'imports_m', 5, 'larger_final_gap_has_priority')

    body += reset() + country('GER', export_target_m=6, tariff=0) + country('SOV', export_target_m=10, tariff=2.5)
    body += country('FRA', import_target_m=4, tariff=1, demand_m=100)
    body += country('ENG', import_target_m=5, tariff=1, demand_m=50)
    body += country('LLU', import_target_m=5, tariff=1, demand_m=10)
    body += cycle()
    for tag, value in [('GER', 6), ('SOV', 8)]:
        body += want(tag, 'exports_m', value, tag.lower() + '_exporter_tariff_preference_preserved')
    for tag, value in [('FRA', 4), ('ENG', 5), ('LLU', 5)]:
        body += want(tag, 'imports_m', value, tag.lower() + '_not_overfilled_across_sellers')
    body += conservation('multiple_seller_conservation')

    body += reset() + country('GER', export_target_m=4, tariff=1) + country('SOV', export_target_m=10, tariff=1)
    body += country('FRA', import_target_m=7, demand_m=100) + country('ENG', import_target_m=2, demand_m=50)
    body += cycle()
    body += want('SOV', 'exports_m', 9, 'same_tariff_larger_exporter_still_first')
    body += want('GER', 'exports_m', 0, 'smaller_exporter_waits')

    for sender, target, prefix in [('GER', 'FRA', 'seller_embargo')]:
        body += reset() + country('GER', export_target_m=5)
        body += country('FRA', import_target_m=5, tariff=0, demand_m=100)
        body += country('ENG', import_target_m=5, tariff=1, demand_m=50)
        body += sender + ' = { send_embargo = ' + target + ' }\n' + cycle()
        body += want('FRA', 'imports_m', 0, prefix + '_excludes_top_buyer')
        body += want('ENG', 'imports_m', 5, prefix + '_continues_to_eligible_buyer')
        body += sender + ' = { break_embargo = ' + target + ' }\n'

    body += reset() + country('GER', export_target_m=5, tariff=1)
    body += country('FRA', import_target_m=4, tariff=2.5, demand_m=100)
    body += country('ENG', import_target_m=4, tariff=2.5, demand_m=50) + cycle()
    body += want('FRA', 'tariffs_m', 10, 'buyer_own_tariff_receipt')
    body += want('GER', 'tariffs_m', 5, 'seller_own_tariff_receipt')
    body += country('FRA', import_target_m=1) + 'APDC_eco_validate_world_trade = yes\n'
    body += want('FRA', 'imports_m', 1, 'daily_validation_reduces_imports')
    body += want('GER', 'exports_m', 2, 'daily_validation_reduces_paired_exports')
    body += country('FRA', import_target_m=4) + 'APDC_eco_validate_world_trade = yes\n'
    body += want('FRA', 'imports_m', 1, 'daily_validation_does_not_rematch')
    body += cycle() + want('FRA', 'imports_m', 4, 'weekly_rematch_restores_priority_quota')
    body += 'APDC_eco_render_trade = yes\nset_variable = { QA_priority_display_sum = 0 }\nfor_each_loop = { array = APDC_eco_trade_amounts add_to_variable = { QA_priority_display_sum = v } }\n'
    body += assertion('seller_display_matches_exports', 'check_variable = { QA_priority_display_sum = -5 } check_variable = { APDC_eco_trade_partners^num = APDC_eco_trade_amounts^num }')
    body += 'send_embargo = FRA\nAPDC_eco_validate_world_trade = yes\n'
    body += want('FRA', 'imports_m', 0, 'active_embargo_cancels_existing_deal')
    body += want('ENG', 'imports_m', 1, 'daily_cancel_does_not_redirect_supply')
    body += want('GER', 'exports_m', 1, 'active_embargo_keeps_paired_quantities')
    body += cycle() + want('ENG', 'imports_m', 4, 'next_week_uses_remaining_eligible_demand')
    body += 'break_embargo = FRA\n'

    body += reset() + country('GER', export_target_m=3, tariff=0) + country('SOV', export_target_m=5, tariff=1)
    body += country('FRA', import_target_m=6, demand_m=100) + country('ENG', import_target_m=2, demand_m=50)
    body += country('GER', exports_m=0) + country('FRA', imports_m=0)
    body += 'set_variable = { QA_priority_active_before = global.APDC_eco_market_active_buffer }\nAPDC_eco_market_begin = yes\nAPDC_eco_market_step = yes\n'
    body += assertion('partial_batch_keeps_current_buffer', 'has_global_flag = APDC_eco_market_busy check_variable = { global.APDC_eco_market_active_buffer = QA_priority_active_before }')
    body += want('FRA', 'imports_m', 0, 'partial_batch_does_not_publish_imports')
    body += want('GER', 'exports_m', 0, 'partial_batch_does_not_publish_exports')
    body += 'APDC_eco_market_step = yes\n'
    body += assertion('completed_batch_switches_plan', 'NOT = { has_global_flag = APDC_eco_market_busy }')
    body += want('FRA', 'imports_m', 6, 'next_seller_finishes_first_buyer')
    body += want('ENG', 'imports_m', 2, 'next_seller_then_fills_second_buyer')
    body += conservation('batch_publish_conservation')

    body += 'set_global_flag = APDC_eco_market_busy\nclr_global_flag = APDC_eco_market_priority_v1\nset_variable = { QA_priority_active_before = global.APDC_eco_market_active_buffer }\nAPDC_eco_market_bootstrap = yes\n'
    body += assertion('old_save_restarts_only_pending_plan', 'has_global_flag = APDC_eco_market_priority_v1 has_global_flag = APDC_eco_market_requested NOT = { has_global_flag = APDC_eco_market_busy } check_variable = { global.APDC_eco_market_active_buffer = QA_priority_active_before }')
    body += want('FRA', 'imports_m', 6, 'old_save_keeps_live_imports')
    body += 'APDC_eco_market_daily = yes\n'
    body += assertion('old_save_rebuild_is_batched', 'has_global_flag = APDC_eco_market_busy check_variable = { global.APDC_eco_market_cursor = 1 }')
    body += 'APDC_eco_market_step = yes\n' + conservation('old_save_rebuild_conservation')

    body += reset() + country('GER', export_target_m=5) + cycle()
    body += want('GER', 'exports_m', 0, 'no_buyers_no_exports')
    body += reset() + country('FRA', import_target_m=5, demand_m=100) + cycle()
    body += want('FRA', 'imports_m', 0, 'no_sellers_no_imports')

    body += reset() + country('SOV', export_target_m=5)
    body += country('ENG', import_target_m=5, tariff=0, demand_m=100)
    body += country('FRA', import_target_m=5, tariff=1, demand_m=50)
    body += 'SOV = { declare_war_on = { target = ENG type = annex_everything } }\n'
    body += assertion('war_fixture_is_active', 'SOV = { has_war_with = ENG }')
    body += cycle() + want('ENG', 'imports_m', 0, 'war_excludes_highest_priority_buyer')
    body += want('FRA', 'imports_m', 5, 'war_skips_to_next_eligible_buyer')
    body += 'SOV = { white_peace = { tag = ENG } }\n'
    body += conservation('war_filter_conservation')

    # Native break_embargo uses ROOT rather than THIS. Test the foreign
    # sender last so its embargo cannot contaminate later GER/FRA fixtures;
    # the relation remains only inside this disposable validation profile.
    body += reset() + country('GER', export_target_m=5)
    body += country('FRA', import_target_m=5, tariff=0, demand_m=100)
    body += country('ENG', import_target_m=5, tariff=1, demand_m=50)
    body += 'FRA = { send_embargo = GER }\n' + cycle()
    body += want('FRA', 'imports_m', 0, 'buyer_embargo_excludes_top_buyer')
    body += want('ENG', 'imports_m', 5, 'buyer_embargo_continues_to_eligible_buyer')

    body += 'every_country = { APDC_eco_refresh_policies = yes APDC_eco_calculate_country = yes }\n' + cycle()
    body += 'log = "APDC_PRIORITY COMPLETE"\n'
    driver = profile / 'driver/common/scripted_effects'
    driver.mkdir(parents=True)
    (driver / 'APDC_market_priority_qa.txt').write_text(block('QA_market_priority', body), 'utf-8')
    on = 'on_actions = { on_daily_GER = { effect = { if = { limit = { NOT = { has_country_flag = QA_priority_done } } set_country_flag = QA_priority_done QA_market_priority = yes } log = "APDC_PRIORITY DAY [GetDateText]" } } }\n'
    (profile / 'driver/common/on_actions/zzzz_APDC_performance_qa.txt').write_text(on, 'utf-8')
    (OUT / 'qa-profile.txt').write_text(str(profile), 'utf-8')
    (OUT / 'expected-assertions.json').write_text(json.dumps(names, indent=2), 'utf-8')
    docs = Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
    protected = [docs / n for n in ['dlc_load.json', 'settings.txt', 'continue_game.json', 'save games/autosave.hoi4']]
    (OUT / 'user-files-before.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}, indent=2), 'utf-8')
    print(profile, 'assertions:', len(names))


def verify():
    profile = Path((OUT / 'qa-profile.txt').read_text('utf-8'))
    text = (profile / 'logs/game.log').read_text('utf-8-sig')
    results = re.findall(r'APDC_PRIORITY (PASS|FAIL) ([^\r\n]+)', text)
    expected = json.loads((OUT / 'expected-assertions.json').read_text('utf-8'))
    failures = [name for result, name in results if result != 'PASS']
    observed = [name for _, name in results]
    assert observed == expected and not failures and 'APDC_PRIORITY COMPLETE' in text, {'failures': failures, 'missing': sorted(set(expected) - set(observed))}
    report = {'profile': str(profile), 'passed': len(results), 'failed': failures, 'assertions': observed,
              'uses_actual_project_effects_and_native_scorers': True, 'visual_verified': False}
    (OUT / 'runtime-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print('PASS:', len(results), 'native trade priority and preservation assertions')


if __name__ == '__main__':
    verify() if '--verify' in sys.argv else prepare()
