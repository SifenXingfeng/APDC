"""Shared, display-only base-1000 formatting for economy quantities."""
from dataclasses import dataclass
from common import block, calc, cond, setv

UNITS = ('', 'K', 'M', 'B', 'T', 'Qa', 'Qi', 'Sx', 'Sp', 'Oc', 'No', 'Dc')


def compare(expression, op, number):
    return f'check_variable = {{ {expression} {op} {number} }}'


def magnitude_at_least(expression, number):
    # Clausewitz NOT with several children is not NOT(AND(children)).
    return 'OR = { NOT = { ' + compare(expression, '<', number) + ' } NOT = { ' + compare(expression, '>', -number) + ' } }'


@dataclass
class Number:
    value: str
    unit: str
    effect: str


def normalize(value, unit):
    # Native fixed-point division can overflow its intermediate numerator for
    # large values. Scale down with small multipliers, two unit tiers at once
    # above one million, without changing the underlying economic value.
    large = magnitude_at_least(value, 1000000) + ' ' + compare(unit, '<', len(UNITS) - 2)
    high = magnitude_at_least(value, 1000) + ' ' + compare(unit, '<', len(UNITS) - 1)
    low = compare(value, '<', 1) + ' ' + compare(value, '>', -1) + ' NOT = { ' + compare(value, '=', 0) + ' } ' + compare(unit, '>', 0)
    return (block('while_loop_effect', 'limit = { ' + large + ' }\nmultiply_variable = { ' + value + ' = 0.00001 }\nmultiply_variable = { ' + value + ' = 0.1 }\nadd_to_variable = { ' + unit + ' = 2 }') +
            block('while_loop_effect', 'limit = { ' + high + ' }\nmultiply_variable = { ' + value + ' = 0.001 }\nadd_to_variable = { ' + unit + ' = 1 }') +
            block('while_loop_effect', 'limit = { ' + low + ' }\nmultiply_variable = { ' + value + ' = 1000 }\nsubtract_from_variable = { ' + unit + ' = 1 }') +
            cond(compare(value, '=', 0), 'set_variable = { ' + unit + ' = 0 }'))


class CompactNumbers:
    def __init__(self, loc, defined):
        self.loc, self.defined = loc, defined
        self.inputs = {}
        self.sl = ''
        self.array_effect = ''

    def scalar(self, expression, base_unit=2, minor=None):
        key = (expression, base_unit, minor)
        if key in self.inputs:
            return self.inputs[key]
        stem = 'ui_number_' + str(len(self.inputs))
        value, unit = 'APDC_eco_' + stem, 'APDC_eco_' + stem + '_unit'
        if minor:
            assert base_unit == 2
            # Near zero, combine in K first. Combining M first would discard
            # sub-ten-ruble precision, including a small negative balance.
            near = compare(expression, '<', 2) + ' ' + compare(expression, '>', -2)
            effect = cond(near,
                          calc(stem, expression, ('multiply', 1000), ('add', minor)) + setv(stem + '_unit', 1),
                          calc(stem, minor, ('divide', 1000), ('add', expression)) + setv(stem + '_unit', 2))
        else:
            effect = setv(stem, expression) + setv(stem + '_unit', base_unit)
        result = Number(value, unit, effect + normalize(value, unit))
        self.inputs[key] = result
        return result

    def trade_array(self):
        value = 'APDC_eco_ui_trade_number'
        unit = 'APDC_eco_ui_trade_number_unit'
        body = 'set_variable = { ' + value + ' = v }\nset_variable = { ' + unit + ' = 2 }\n'
        body += normalize(value, unit)
        body += 'add_to_array = { array = APDC_eco_ui_trade_values value = ' + value + ' }\n'
        body += 'add_to_array = { array = APDC_eco_ui_trade_units value = ' + unit + ' }\n'
        self.array_effect = ('clear_array = APDC_eco_ui_trade_values\nclear_array = APDC_eco_ui_trade_units\n' +
                             block('for_each_loop', 'array = APDC_eco_trade_amounts\n' + body))
        return Number('ROOT.APDC_eco_ui_trade_values^APDC_eco_trade_index',
                      'ROOT.APDC_eco_ui_trade_units^APDC_eco_trade_index', '')

    def variants(self, number):
        return [(number.value, '2', suffix, compare(number.unit, '=', index)) for index, suffix in enumerate(UNITS)]

    def formatted(self, name, number, signed=False):
        rows = []
        for index, suffix in enumerate(UNITS):
            for sign in (('POS', 'NEG', 'ZERO') if signed else ('PLAIN',)):
                key = 'APDC_ECO_NUMBER_' + name + '_' + str(index) + '_' + sign
                field = '[?' + number.value + '|2]'
                condition = compare(number.unit, '=', index)
                if signed:
                    condition += ' ' + compare(number.value, '>' if sign == 'POS' else '<' if sign == 'NEG' else '=', 0)
                    field = '§' + {'POS': 'G', 'NEG': 'R', 'ZERO': 'Y'}[sign] + ('+' if sign == 'POS' else '') + field + '§!'
                self.loc[key] = field + suffix
                rows.append((condition, key))
        self.loc['APDC_ECO_NUMBER_ZERO'] = '0.00'
        self.sl += self.defined(name, rows, 'APDC_ECO_NUMBER_ZERO')
        return '[' + name + ']'

    def effects(self):
        return ''.join(number.effect for number in self.inputs.values()) + self.array_effect


def panel_numbers(numbers, loc):
    cash = numbers.scalar('APDC_eco_cash_m', minor='APDC_eco_cash_k')
    purchase = numbers.scalar('APDC_eco_purchase_cost_m', minor='APDC_eco_purchase_cost_k')
    ruble = '£APDC_ruble_texticon£'
    loc['APDC_ECO_CASH'] = '国库：' + numbers.formatted('APDCEconomyCashAmount', cash) + ruble
    loc['APDC_ECO_WEEKLY'] = '每周变化：' + numbers.formatted('APDCEconomyWeeklyAmount', numbers.scalar('APDC_eco_weekly_balance_m'), signed=True) + ruble
    for key, label, variable in [('DOMESTIC', '总消费品', 'domestic_m'), ('SUPPLY', '供给', 'supply_m'), ('DEMAND', '需求', 'demand_m'),
                                 ('EXTRA_IN', '额外输入消费品', 'extra_input'), ('EXTRA_OUT', '额外输出消费品', 'extra_output'), ('TRADE', '贸易消费品', 'trade_net_m')]:
        name = 'APDCEconomy' + key.title().replace('_', '') + 'Value'
        field = numbers.formatted(name, numbers.scalar('APDC_eco_' + variable), signed=key == 'TRADE')
        loc['APDC_ECO_' + key] = label + '\\n' + field
        if key in ['SUPPLY', 'DEMAND']:
            loc['APDC_ECO_' + key + '_VALUE'] = field
    loc['APDC_ECO_PURCHASE_COST'] = '总价：' + numbers.formatted('APDCEconomyPurchaseAmount', purchase) + ruble
    loc['APDC_ECO_TRADE_COUNTRY_AMOUNT'] = numbers.formatted('APDCEconomyTradeCountryAmount', numbers.trade_array(), signed=True)
    return purchase
