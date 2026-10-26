"""Isolated engine checks for display-only law traits and factory safety."""
import datetime
from pathlib import Path
import sys

from common import ROOT, block, parse


def build():
    sys.path.insert(0, str(ROOT / 'tools/performance'))
    import prepare_runtime
    qa = Path('D:/APDC_FixedLawStatQA_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    prepare_runtime.QA = qa
    prepare_runtime.prepare(toolpack=True)
    driver = qa / 'driver'
    (driver / 'common/defines/zzzz_APDC_performance_qa.lua').write_text(
        'NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.0 }\n', 'utf-8')
    laws = [('undisturbed_isolation', 1), ('isolation', 1), ('civilian_economy', 1),
            ('low_economic_mobilisation', .85), ('partial_economic_mobilisation', .7),
            ('war_economy', .55), ('tot_economic_mobilisation', .4)]
    checks = ''
    for i, (law, value) in enumerate(laws, 1):
        trait = 'APDC_eco_population_display_' + str(round(value * 100))
        body = ''.join('remove_ideas = ' + key + '\n' for key, _ in laws)
        body += 'add_ideas = ' + law + '\nAPDC_eco_refresh_policies = yes\nAPDC_eco_refresh_current_supply = yes\n'
        body += 'set_temp_variable = { QA_native_expected = modifier@consumer_goods_expected_value }\n'
        body += 'set_temp_variable = { QA_native_factor = modifier@consumer_goods_factor }\n'
        condition = ('has_idea_with_trait = ' + trait + ' '
                     'check_variable = { APDC_eco_population_base = ' + str(value) + ' } '
                     'check_variable = { QA_native_expected = -1 } '
                     'check_variable = { QA_native_factor = 0 } '
                     'num_of_civilian_factories_available_for_projects > 0')
        body += 'if = { limit = { ' + condition + ' } log = "APDC_FIXED_STAT PASS ' + law + '" } else = { log = "APDC_FIXED_STAT FAIL ' + law + '" }\n'
        body += ('log = "APDC_FIXED_FACTORY law=' + law + ' total=[?num_of_civilian_factories] '
                 'free=[?num_of_civilian_factories_available_for_projects] assigned=[?APDC_eco_public_civ]"\n')
        body += 'set_variable = { QA_stat_stage = ' + str(i) + ' }\n'
        checks += ('if' if i == 1 else 'else_if') + ' = { limit = { '
        checks += ('NOT = { has_variable = QA_stat_stage }' if i == 1 else 'check_variable = { QA_stat_stage = ' + str(i - 1) + ' }')
        checks += ' }\n' + body + '}\n'
    checks += 'else_if = { limit = { check_variable = { QA_stat_stage = 7 } } '
    checks += ''.join('remove_ideas = ' + key + '\n' for key, _ in laws)
    checks += 'add_ideas = civilian_economy APDC_eco_refresh_policies = yes APDC_eco_refresh_current_supply = yes set_variable = { QA_stat_stage = 8 } log = "APDC_FIXED_STAT RESTORED" }\n'
    # Resolve all literal names in the same country and without changing its
    # active law: this must produce five different labels at the same time.
    folder = driver / 'common/scripted_localisation'
    folder.mkdir(parents=True)
    text = ''
    for value in [100, 85, 70, 55, 40]:
        text += block('defined_text', 'name = APDCFixedStat' + str(value) + '\ntext = { localization_key = APDC_eco_population_display_' + str(value) + ' }')
    (folder / 'APDC_fixed_law_stat_qa.txt').write_text(text, 'utf-8')
    checks += ('log = "APDC_FIXED_LABELS same_country=[THIS.GetTag] '
               'civilian=[APDCFixedStat100] low=[APDCFixedStat85] partial=[APDCFixedStat70] '
               'war=[APDCFixedStat55] total=[APDCFixedStat40]"\n')
    (driver / 'common/on_actions/zzzz_APDC_performance_qa.txt').write_text(
        'on_actions = { on_daily_GER = { effect = {\n' + checks + '} } }\n', 'utf-8')
    (ROOT / 'docs/economy/20261023-fixed-law-stat/profile.txt').write_text(str(qa), 'utf-8')
    print(qa)


if __name__ == '__main__':
    build()
