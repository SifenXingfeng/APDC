"""Compact, nonzero direct contributions for economy hover text."""
from common import calc, check, cond, setv
from number_format import compare

RUBLE = '£APDC_ruble_texticon£'


def augment(data, loc, defined, numbers):
    from build_data import LAWS
    from presentation import descriptions
    desc = descriptions(data)
    sl = ''
    ui = ''
    loc['APDC_ECO_EMPTY'] = ''

    for group, *_ in LAWS:
        name = 'APDCEconomyActive' + group.title().replace('_', '') + 'Tooltip'
        sl += defined(name, [('has_idea = APDC_eco_' + group + '_' + str(j), f'APDC_eco_{group}_{j}_ui_tip') for j in range(1, 6)], 'APDC_ECO_TITLE')
        loc['APDC_ECO_ACTIVE_' + group] = '[' + name + ']'
    sl += defined('APDCEconomyLawTooltip', [(check('selected_group', '=', i) + ' ' + check('law_level', '=', j), f'APDC_eco_{group}_{j}_ui_tip') for i, (group, *_) in enumerate(LAWS, 1) for j in range(1, 6)], 'APDC_ECO_TITLE')
    for group in ['food', 'education', 'medical']:
        for j in range(1, 6):
            loc[f'APDC_ECO_{group}_{j}_TIP'] = desc[f'APDC_eco_{group}_{j}_ui_tip']

    def line(slot, label, variable, *, percent=False, base=False, active='', quantity=False, currency=False, minor=None):
        """The whole line, including its newline, disappears at exactly zero."""
        nonlocal sl
        name = 'APDCEconomySource' + ''.join(x.title() for x in slot.split('_'))
        branches = []
        sign_expression = 'APDC_eco_' + variable
        variants = [(sign_expression, '2%' if percent else '2', '', '')]
        if quantity:
            number = numbers.scalar(sign_expression, minor=minor)
            variants = numbers.variants(number)
            sign_expression = number.value
        for index, (display, fmt, unit, scale_condition) in enumerate(variants):
            for sign, op in [('POS', '>'), ('NEG', '<')]:
                key = 'APDC_ECO_SOURCE_' + slot.upper() + '_' + str(index) + '_' + sign
                colour = 'Y' if base else 'G' if sign == 'POS' else 'R'
                number = ('+' if sign == 'POS' else '') + '[?' + display + '|' + fmt + ']'
                loc[key] = label + '：§' + colour + number + '§!' + unit + (RUBLE if currency else '') + '\\n'
                branches.append((active + ' ' + compare(sign_expression, op, 0) + ' ' + scale_condition, key))
        sl += defined(name, branches, 'APDC_ECO_EMPTY')
        return '[' + name + ']'

    def fixed(slot, label, value, suffix='', active=''):
        nonlocal sl
        key = 'APDC_ECO_SOURCE_' + slot.upper()
        loc[key] = label + '：§Y+' + f'{value:.2f}' + suffix + '§!\\n'
        if not active:
            return '$' + key + '$'
        name = 'APDCEconomySource' + ''.join(x.title() for x in slot.split('_'))
        sl += defined(name, [(active, key)], 'APDC_ECO_EMPTY')
        return '[' + name + ']'

    def tooltip(key, title, rows):
        loc[key] = '§Y' + title + '§!\\n\\n' + ''.join(rows)

    # These are the final treasury contributions, with spending negated once.
    budget = []
    for label, variable in [('人口税', 'head_tax_m'), ('消费税', 'consumption_tax_m'), ('关税', 'tariffs_m')]:
        budget.append(line('weekly_' + variable, label, variable, quantity=True, currency=True))
    for label, variable in [('人口开支', 'welfare_cost_m'), ('消费补贴', 'subsidies_m'), ('消费品工厂投资', 'investment_cost_m'), ('建设维护', 'construction_cost_m'), ('军工生产维护', 'production_cost_m'), ('船坞生产维护', 'naval_production_cost_m'), ('科研维护', 'research_cost_m'), ('专项计划维护', 'projects_cost_m'), ('陆军维护', 'army_cost_m'), ('海军维护', 'navy_cost_m'), ('空军维护', 'air_cost_m')]:
        target = 'ui_weekly_' + variable
        ui += calc(target, 0, ('subtract', 'APDC_eco_' + variable))
        budget.append(line('weekly_' + variable, label, target, quantity=True, currency=True))
    tooltip('APDC_ECO_WEEKLY_TIP', '国库每周变化', budget)
    tooltip('APDC_ECO_CASH_TIP', '国库', [line('cash_balance', '当前余额', 'cash_m', base=True, quantity=True, currency=True, minor='APDC_eco_cash_k')])

    def policy_sources(slot, target, *, percent=False, active=''):
        nonlocal sl, ui
        residual = 'ui_' + slot + '_other'
        ui += setv(residual, 'modifier@APDC_eco_' + target)
        result = []
        for source, group in data.items():
            rows = []
            for level, entry in enumerate(group['entries'], 1):
                amount = entry['custom'].get('APDC_eco_' + target, 0)
                if not amount:
                    continue
                eid = f'APDC_eco_{source}_{level}'
                key = f'APDC_ECO_SOURCE_{slot}_{source}_{level}'
                numeric = f'{amount * (100 if percent else 1):+.2f}' + ('%' if percent else '')
                loc[key] = entry['name'] + '：§' + ('G' if amount > 0 else 'R') + numeric + '§!\\n'
                rows.append((active + ' has_idea = ' + eid, key))
                ui += cond('has_idea = ' + eid, calc(residual, 'APDC_eco_' + residual, ('subtract', amount)))
            if rows:
                name = 'APDCEconomySource' + ''.join(x.title() for x in (slot + '_' + source).split('_'))
                sl += defined(name, rows, 'APDC_ECO_EMPTY')
                result.append('[' + name + ']')
        result.append(line(slot + '_other', '其他修正', residual, percent=percent, active=active))
        return result

    for group, label in [('food', '温饱'), ('education', '教育'), ('medical', '医疗')]:
        rows = policy_sources(group + '_weekly', group + '_weekly')
        if group == 'food':
            rows.append(line('food_shortage', '消费品缺口', 'food_penalty'))
        tooltip('APDC_ECO_' + group.upper() + '_WEEKLY_TIP', label + '水平每周变化', rows)

    # Domestic total contains domestic production only, not trade or allocation.
    ui += calc('ui_domestic_public_m', 'APDC_eco_public_civ', ('multiply', 'APDC_eco_goods_per_civ_m'))
    ui += calc('ui_domestic_private_m', 'APDC_eco_domestic_m', ('subtract', 'APDC_eco_ui_domestic_public_m'))
    tooltip('APDC_ECO_DOMESTIC_TIP', '总消费品来源', [
        line('domestic_public', '国营民工生产', 'ui_domestic_public_m', quantity=True),
        line('domestic_private', '私营民工生产', 'ui_domestic_private_m', quantity=True)])

    ui += calc('ui_distribution_speed', 'APDC_eco_distribution_capacity_input', ('clamp', '{ min = 0 max = 50 }'), ('multiply', -.004))
    ui += setv('ui_distribution_bonus', 'modifier@APDC_eco_distribution_bonus')
    ui += calc('ui_planned_distribution', 'political_power_daily', ('multiply', .15))
    ui += calc('ui_distribution_boundary', 'APDC_eco_distribution', ('subtract', .8), ('subtract', 'APDC_eco_ui_distribution_speed'), ('subtract', 'APDC_eco_ui_distribution_bonus'))
    ui += cond('APDC_eco_is_planned = yes', calc('ui_distribution_boundary', 'APDC_eco_distribution', ('subtract', .6), ('subtract', 'APDC_eco_ui_planned_distribution')))
    rows = [fixed('distribution_market_base', '基础分配率', 80, '%'),
            line('distribution_speed', '私营产业建设', 'ui_distribution_speed', percent=True)]
    rows += policy_sources('distribution', 'distribution_bonus', percent=True)
    rows.append(line('distribution_market_boundary', '分配率边界', 'ui_distribution_boundary', percent=True))
    tooltip('APDC_ECO_DISTRIBUTION_MARKET_TIP', '分配率来源', rows)
    tooltip('APDC_ECO_DISTRIBUTION_PLANNED_TIP', '分配率来源', [
        fixed('distribution_planned_base', '基础分配率', 60, '%'),
        line('distribution_political_power', '政治点数净增长', 'ui_planned_distribution', percent=True),
        line('distribution_planned_boundary', '分配率边界', 'ui_distribution_boundary', percent=True)])
    sl += defined('APDCEconomyDistributionTooltip', [('APDC_eco_is_planned = yes', 'APDC_ECO_DISTRIBUTION_PLANNED_TIP')], 'APDC_ECO_DISTRIBUTION_MARKET_TIP')
    loc['APDC_ECO_DISTRIBUTION_TIP'] = '[APDCEconomyDistributionTooltip]'

    for kind, label, building in [('civ', '民工', 'industrial_complex'), ('mil', '军工', 'arms_factory')]:
        growing = check(kind + '_velocity', '>', 0)
        ui += calc('ui_' + kind + '_base_contribution', 'modifier@APDC_eco_' + kind + '_expansion_base', ('multiply', 'APDC_eco_private_civ'), ('multiply', .5))
        for attr in ['production_speed_buildings_factor', 'production_speed_' + building + '_factor']:
            ui += setv('ui_' + attr, 'modifier@' + attr)
        rows = [line(kind + '_private_base', '私营民工基础建设', 'ui_' + kind + '_base_contribution', base=True, active=growing),
                fixed(kind + '_white_base', '基础产能', 2.5, active=growing),
                line(kind + '_general_speed', '通用建设速度', 'ui_production_speed_buildings_factor', percent=True, active=growing),
                line(kind + '_building_speed', label + '建设速度', 'ui_production_speed_' + building + '_factor', percent=True, active=growing)]
        rows += policy_sources(kind + '_expansion', 'private_' + kind + '_expansion_factor', percent=True, active=growing)
        rows += [line(kind + '_shortage', '消费品缺口', 'shortage', percent=True, active=growing),
                 line(kind + '_closure', '产能过剩倒闭', kind + '_velocity', active=check(kind + '_velocity', '<', 0))]
        tooltip('APDC_ECO_' + kind.upper() + '_BUILD_TIP', '私营' + label + '建设来源', rows)
        sl += defined('APDCEconomy' + kind.title() + 'BuildTooltip', [], 'APDC_ECO_' + kind.upper() + '_BUILD_TIP')
        # The UI key resolves the body directly; the named wrapper remains for
        # existing debug/QA callers without introducing a localisation cycle.
    return sl, ui
