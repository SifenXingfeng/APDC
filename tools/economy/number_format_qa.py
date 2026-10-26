"""Engine checks for compact units, two-part money and scoped trade rows."""
import json
import re
from pathlib import Path

from common import ROOT, WORK, parse
import direct_tooltip_qa

OUT = WORK / '20261023-number-units'


def prepare():
    direct_tooltip_qa.prepare(OUT)
    profile = Path((OUT / 'qa-profile.txt').read_text('utf-8'))
    path = profile / 'driver/common/scripted_effects/APDC_panel_qa.txt'
    raw = path.read_text('utf-8')
    fixture = next(n for n in parse(raw) if n.key == 'QA_panel_fixtures')
    extra = ''
    expected = {}

    def sample(marker, changes, fields, result, refresh='APDC_eco_refresh_number_ui'):
        nonlocal extra
        extra += changes + '\n' + refresh + ' = yes\n'
        extra += 'log = "APDC_UNITS ' + marker + ' |' + '|'.join('[' + field + ']' for field in fields) + '|"\n'
        expected[marker] = result

    for marker, whole, kilo, result in [
        ('ZERO', '0', '0', '0.00'), ('RAW', '0', '0.99999', '999.99'),
        ('K', '0', '1', '1.00K'), ('K_HIGH', '0', '999.99', '999.99K'),
        ('M', '1', '0', '1.00M'), ('M_HIGH', '999', '990', '999.99M'),
        ('B', '1000', '0', '1.00B'), ('T', '1000000', '0', '1.00T'),
        ('QA', '1000000000', '0', '1.00Qa'), ('QI', '1000000000', '0', '1.00Qi'),
        ('NEG_RAW', '-1', '999.99828', '-1.72'), ('NEG_K', '-1', '998.75', '-1.25K'),
        ('NEG_M', '-2', '750', '-1.25M'), ('NEG_B', '-1250', '0', '-1.25B')]:
        changes = f'set_variable = {{ APDC_eco_cash_m = {whole} }} set_variable = {{ APDC_eco_cash_k = {kilo} }}'
        if marker == 'QI':
            # Avoid both the 32-bit integer literal reader and overflow in
            # fixed-point multiplication when constructing this test input.
            changes = 'set_variable = { APDC_eco_cash_m = 0 } set_variable = { APDC_eco_cash_k = 0 } set_temp_variable = { QA_units_increment = 1000000000 }'
            for bit in range(10):
                if 1000 & (1 << bit):
                    changes += ' add_to_variable = { APDC_eco_cash_m = QA_units_increment }'
                if bit < 9:
                    changes += ' add_to_temp_variable = { QA_units_increment = QA_units_increment }'
        sample(marker, changes,
               ['APDCEconomyCashAmount'], result)
    sample('SUPPLY', 'set_variable = { APDC_eco_supply_m = 1250 }', ['APDCEconomySupplyValue'], '1.25B')
    sample('DOMESTIC', 'set_variable = { APDC_eco_domestic_m = 0.0025 }', ['APDCEconomyDomesticValue'], '2.50K')
    sample('DEMAND', 'set_variable = { APDC_eco_demand_m = 1250000 }', ['APDCEconomyDemandValue'], '1.25T')
    sample('EXTRA_IN', 'set_variable = { APDC_eco_extra_input = 0.00025 }', ['APDCEconomyExtraInValue'], '250.00')
    sample('EXTRA_OUT', 'set_variable = { APDC_eco_extra_output = 1.25 }', ['APDCEconomyExtraOutValue'], '1.25M')
    sample('TRADE_NET', 'set_variable = { APDC_eco_trade_net_m = -1250 }', ['APDCEconomyTradeValue'], '§R-1.25§!B')
    sample('WEEKLY', 'set_variable = { APDC_eco_weekly_balance_m = 1250 }', ['APDCEconomyWeeklyAmount'], '§G+1.25§!B')
    sample('PURCHASE_SMALL', 'set_variable = { APDC_eco_purchase_cost_m = 0 } set_variable = { APDC_eco_purchase_cost_k = 0.0172 }', ['APDCEconomyPurchaseAmount'], '17.20', refresh='APDC_eco_refresh_purchase_number_ui')
    sample('PURCHASE_COMBINED', 'set_variable = { APDC_eco_purchase_cost_m = 1 } set_variable = { APDC_eco_purchase_cost_k = 234.56 }', ['APDCEconomyPurchaseAmount'], '1.23M', refresh='APDC_eco_refresh_purchase_number_ui')
    sample('SOURCE_B', 'set_variable = { APDC_eco_head_tax_m = 1250 }', ['APDCEconomySourceWeeklyHeadTaxM'], '§G+1.25§!B')
    sample('SOURCE_T', 'set_variable = { APDC_eco_construction_cost_m = 1250000 }', ['APDCEconomySourceWeeklyConstructionCostM'], '§R-1.25§!T', refresh='APDC_eco_sync_ui')
    item = next(e for e in json.loads((WORK/'equipment_catalogue.json').read_text('utf-8')) if e['id'] == 'infantry_equipment_0')
    idx = item['index']
    extra += f'set_variable = {{ APDC_eco_stocks^{idx} = 20 }} set_temp_variable = {{ APDC_eco_equipment_id = {idx} }}\nQA_click_eq_buy = yes\n'
    extra += 'log = "APDC_UNITS PURCHASE_BUTTON_ONE |[APDCEconomyPurchaseAmount]|"\n'
    expected['PURCHASE_BUTTON_ONE'] = '86.00'
    extra += 'QA_click_qty_add_10 = yes\nlog = "APDC_UNITS PURCHASE_BUTTON_ADD |[APDCEconomyPurchaseAmount]|"\n'
    expected['PURCHASE_BUTTON_ADD'] = '946.00'
    extra += 'QA_click_qty_max = yes\nlog = "APDC_UNITS PURCHASE_BUTTON_MAX |[APDCEconomyPurchaseAmount]|"\n'
    expected['PURCHASE_BUTTON_MAX'] = '1.72K'
    extra += 'clear_array = APDC_eco_trade_amounts\nadd_to_array = { array = APDC_eco_trade_amounts value = 1250 }\nadd_to_array = { array = APDC_eco_trade_amounts value = -0.005 }\nAPDC_eco_refresh_number_ui = yes\n'
    extra += 'FRA = { set_temp_variable = { APDC_eco_trade_index = 0 } log = "APDC_UNITS TRADE_ROW_B |[APDCEconomyTradeCountryAmount]|" set_temp_variable = { APDC_eco_trade_index = 1 } log = "APDC_UNITS TRADE_ROW_K |[APDCEconomyTradeCountryAmount]|" }\n'
    expected['TRADE_ROW_B'] = '§G+1.25§!B'
    expected['TRADE_ROW_K'] = '§R-5.00§!K'
    extra += 'QA_click_back = yes\nlog = "APDC_UNITS COMPLETE"\n'
    path.write_text(raw[:fixture.value_end - 1] + extra + raw[fixture.value_end - 1:], 'utf-8')
    (OUT/'expected-units.json').write_text(json.dumps(expected, ensure_ascii=False, indent=2), 'utf-8')
    print(profile)


def verify():
    direct_tooltip_qa.verify(OUT)
    profile = Path((OUT/'qa-profile.txt').read_text('utf-8'))
    raw = (profile/'logs/game.log').read_text('utf-8-sig')
    samples = dict(re.findall(r'APDC_UNITS ([A-Z_]+) \|(.*?)\|', raw, re.S))
    samples = {k: v.replace('\x11', '§').replace('\x13', '£') for k, v in samples.items()}
    expected = json.loads((OUT/'expected-units.json').read_text('utf-8'))
    failures = {name: samples.get(name) for name, value in expected.items()
                if (value not in samples.get(name, '') if name.startswith('SOURCE_') else samples.get(name) != value)}
    assert not failures, failures
    report = json.loads((OUT/'runtime-verification.json').read_text('utf-8'))
    report.update({'unit_checks_passed': len(expected), 'unit_samples': samples})
    (OUT/'runtime-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print('PASS:', len(expected), 'unit, sign, precision and trade-scope checks')


if __name__ == '__main__':
    import sys
    verify() if '--verify' in sys.argv else prepare()
