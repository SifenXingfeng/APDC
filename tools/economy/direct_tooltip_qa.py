"""Isolated engine checks for nonzero direct-contribution hover lines."""
import json
import re
from pathlib import Path

from common import ROOT, parse
from panel_qa import build


def prepare(output=None):
    output = output or ROOT / 'docs/economy/20261023-direct-source-tooltips'
    build(output)
    profile = Path((output / 'qa-profile.txt').read_text('utf-8'))
    path = profile / 'driver/common/scripted_effects/APDC_panel_qa.txt'
    raw = path.read_text('utf-8')
    fixture = next(n for n in parse(raw) if n.key == 'QA_panel_fixtures')
    extra = ''

    def sample(marker, changes, functions, sync=True):
        nonlocal extra
        extra += changes + ('\nAPDC_eco_sync_ui = yes\n' if sync else '\n')
        extra += 'log = "APDC_DIRECT ' + marker + ' |' + '|'.join('[' + name + ']' for name in functions) + '|"\n'

    income = 'APDCEconomySourceWeeklyHeadTaxM'
    cost = 'APDCEconomySourceWeeklyConstructionCostM'
    shortage = 'APDCEconomySourceFoodShortage'
    sample('ZERO', 'set_variable = { APDC_eco_head_tax_m = 0 } set_variable = { APDC_eco_construction_cost_m = 0 } set_variable = { APDC_eco_food_penalty = 0 }', [income, cost, shortage])
    sample('INCOME', 'set_variable = { APDC_eco_head_tax_m = 1.25 }', [income])
    sample('COST', 'set_variable = { APDC_eco_construction_cost_m = 2.5 }', [cost])
    sample('NEGATIVE_COST', 'set_variable = { APDC_eco_construction_cost_m = -2.5 }', [cost])
    sample('SMALL_MONEY', 'set_variable = { APDC_eco_head_tax_m = 0.005 }', [income])
    sample('TINY_MONEY', 'set_variable = { APDC_eco_head_tax_m = 0.00025 }', [income])
    sample('FOOD_PENALTY', 'set_variable = { APDC_eco_food_penalty = -0.05 }', [shortage])
    sample('ZERO_GOODS', 'set_variable = { APDC_eco_public_civ = 0 } set_variable = { APDC_eco_domestic_m = 0 }', ['APDCEconomySourceDomesticPublic', 'APDCEconomySourceDomesticPrivate'])
    sample('STOPPED', 'set_variable = { APDC_eco_civ_velocity = 0 } set_variable = { APDC_eco_mil_velocity = 0 }', ['APDCEconomyCivBuildTooltip', 'APDCEconomyMilBuildTooltip'])
    sample('GROWTH', 'set_variable = { APDC_eco_civ_velocity = 1 }', ['APDCEconomyCivBuildTooltip'])
    sample('CLOSURE', 'set_variable = { APDC_eco_civ_velocity = -2.5 }', ['APDCEconomyCivBuildTooltip'])
    sample('ZERO_POLITICAL', 'set_variable = { APDC_eco_ui_planned_distribution = 0 }', ['APDCEconomySourceDistributionPoliticalPower'], sync=False)
    sample('POLITICAL_BONUS', 'set_variable = { APDC_eco_ui_planned_distribution = 0.15 }', ['APDCEconomySourceDistributionPoliticalPower'], sync=False)
    extra += 'QA_click_back = yes\nlog = "APDC_DIRECT COMPLETE"\n'
    raw = raw[:fixture.value_end - 1] + extra + raw[fixture.value_end - 1:]
    path.write_text(raw, 'utf-8')
    print(profile)


def verify(output=None):
    output = output or ROOT / 'docs/economy/20261023-direct-source-tooltips'
    profile = Path((output / 'qa-profile.txt').read_text('utf-8'))
    raw = (profile / 'logs/game.log').read_text('utf-8-sig')
    cases = dict(re.findall(r'APDC_DIRECT ([A-Z_]+) (.*?)(?=\n\[|\Z)', raw, re.S))
    cases = {k: v.strip().replace('\x11', '§').replace('\x13', '£') for k, v in cases.items()}
    expected = {
        'ZERO': lambda s: s == '||||',
        'INCOME': lambda s: '§G+1.25§!M' in s,
        'COST': lambda s: '§R-2.50§!M' in s,
        'NEGATIVE_COST': lambda s: '§G+2.50§!M' in s,
        'SMALL_MONEY': lambda s: '§G+5.00§!K' in s,
        'TINY_MONEY': lambda s: '§G+250.00§!£APDC_ruble_texticon£' in s,
        'FOOD_PENALTY': lambda s: '§R-0.05§!' in s and '×' not in s,
        'ZERO_GOODS': lambda s: s == '|||',
        'STOPPED': lambda s: '：' not in s and '0.00' not in s,
        'GROWTH': lambda s: '基础产能：§Y+2.50§!' in s and '§G+38.00%§!' in s and '§R-30.00%§!' in s,
        'CLOSURE': lambda s: '产能过剩倒闭：§R-2.50§!' in s and s.count('：') == 1,
        'ZERO_POLITICAL': lambda s: s == '||',
        'POLITICAL_BONUS': lambda s: '§G+15.00%§!' in s}
    failures = [name for name, predicate in expected.items() if name not in cases or not predicate(cases[name])]
    old = re.findall(r'APDC_PANEL_ASSERT (PASS|FAIL) ([^\r\n]+)', raw)
    failures += [name for result, name in old if result != 'PASS']
    assert len(old) == 60, len(old)
    assert not failures, failures
    for content in cases.values():
        assert all(t not in content for t in [' = ', ' × ', 'max(', 'clamp(', '有效私营民工', '当前进度：', '每座最终产能'])
    report = {'profile': str(profile), 'existing_checks_passed': 60, 'direct_display_checks_passed': len(expected),
              'failed': failures, 'resolved_samples': cases, 'visual_verified': False}
    (output / 'runtime-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print('PASS: 60 existing checks; 13 direct source, zero, sign and unit checks')


if __name__ == '__main__':
    import sys
    verify() if '--verify' in sys.argv else prepare()
