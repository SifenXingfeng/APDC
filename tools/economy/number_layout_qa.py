"""Read-only fit checks using the effective bitmap font glyph metrics."""
import json
import re
from functools import lru_cache
from pathlib import Path

from common import ROOT, GAME, parse, walk
from number_format import UNITS

OUT = ROOT / 'docs/economy/20261023-number-width'


@lru_cache(None)
def font(name, chinese):
    files = [GAME / 'gfx/fonts' / (name + '.fnt')]
    if chinese:
        suffix = '_?of4.fnt' if name == 'hoi_24header' else '_?of4EX.fnt'
        files = sorted((GAME / 'gfx/fonts/chinese').glob(name + suffix)) + files
    chars, height, kernings = {}, 0, {}
    for path in files:
        for line in path.read_text('utf-8-sig').splitlines():
            fields = {k: int(v) for k, v in re.findall(r'(\w+)=\s*(-?\d+)', line)}
            if line.startswith('common ') and not height:
                height = fields['lineHeight']
            elif line.startswith('char '):
                chars.setdefault(fields['id'], fields)
            elif line.startswith('kerning '):
                kernings.setdefault((fields['first'], fields['second']), fields['amount'])
    return chars, height, kernings


def bounds(value, name, chinese):
    chars, line_height, kernings = font(name, chinese)
    widths, ink = [], []
    for index, line in enumerate(value.split('\n')):
        pen, left, right, top, bottom = 0, 0, 0, 0, 0
        previous = None
        # Keep the real inline ruble sprite's 15x20 dimensions in the audit.
        for token in re.findall(r'£APDC_ruble_texticon£|.', line):
            current = None if token.startswith('£') else ord(token)
            pen += kernings.get((previous, current), 0)
            d = ({'xadvance': 15, 'xoffset': 0, 'width': 15, 'yoffset': 0, 'height': 20}
                 if token.startswith('£') else chars[ord(token)])
            left = min(left, pen + d['xoffset'])
            right = max(right, pen + d['xoffset'] + d['width'])
            top = min(top, index * line_height + d['yoffset'])
            bottom = max(bottom, index * line_height + d['yoffset'] + d['height'])
            pen += d['xadvance']
            previous = current
        widths.append(pen)
        ink.append((left, right, top, bottom))
    return widths, ink


def run():
    nodes = {n.val('name'): n for n in walk(parse((ROOT / 'interface/APDC_economy_panel.gui').read_text('utf-8')))
             if n.key == 'instantTextboxType'}
    samples = [d * 3 + '.' + d * 2 for d in '0123456789'] + ['0.00', '1.00', '999.99']
    specs = {
        'cash': ('国库：{n}£APDC_ruble_texticon£', True),
        'weekly': ('每周变化：{n}£APDC_ruble_texticon£', True),
        'domestic': ('总消费品\n{n}', False),
        'supply_value': ('{n}', False), 'demand_value': ('{n}', False),
        'extra_in': ('额外输入消费品\n{n}', False),
        'extra_out': ('额外输出消费品\n{n}', False),
        'trade_label': ('贸易消费品\n{n}', True),
        'trade_amount': ('{n}', True),
        'purchase_cost': ('总价：{n}£APDC_ruble_texticon£', True),
        'dist': ('分配率\n100.0%', False),
    }
    for kind in ['food', 'education', 'medical']:
        specs[kind + '_weekly'] = ('+99.99/周', False)
    report = {'fields': {}, 'failures': [], 'visual_verified': False,
              'method': 'Native bitmap font advances, pair kerning and ink bounds, including outline, both native ASCII and Chinese overrides; all compact suffixes and signs.'}
    for suffix, (template, signed) in specs.items():
        node = nodes['APDC_eco_' + suffix]
        assert node.val('truncate') == 'no', suffix
        width, height = int(node.val('maxWidth')), int(node.val('maxHeight'))
        name = node.val('font')
        strings = [template.format(n=sign + number + unit) for number in samples for unit in UNITS
                   for sign in (['', '-', '+'] if signed else [''])] if '{n}' in template else [template]
        worst_width, worst_text, min_margin, count = 0, '', width, 0
        for chinese in [True, False]:
            for value in strings:
                # Non-ASCII labels use Chinese metrics; the second pass audits
                # numeric runs in the original font, without assuming CJK glyphs.
                if not chinese:
                    value = '\n'.join(re.sub(r'[^\x00-\x7f£]', '', line) for line in value.split('\n'))
                    value = value.replace('£APDC_ruble_texticon£', '')
                advances, ink = bounds(value, name, chinese)
                count += 1
                for advance, (left, right, _, _) in zip(advances, ink):
                    actual = max(advance, right) - min(0, left)
                    margin = min((width - advance) / 2 + left, width - ((width - advance) / 2 + right))
                    min_margin = min(min_margin, margin)
                    if actual > worst_width:
                        worst_width, worst_text = actual, value
                    if margin < 0:
                        report['failures'].append([suffix, 'width', value, actual, width])
                block_height = max(b for _, _, _, b in ink) - min(t for _, _, t, _ in ink)
                if block_height > height:
                    report['failures'].append([suffix, 'height', value, block_height, height])
        report['fields'][suffix] = {'font': name, 'box': [width, height], 'cases': count,
                                   'widest_ink_px': worst_width, 'widest_sample': worst_text,
                                   'minimum_horizontal_margin_px': min_margin}
    # The two amount columns have their own positions. Check their widest
    # possible positive strings together, rather than only checking each box.
    gaps = {}
    for chinese in [True, False]:
        rectangles = []
        for suffix in ['supply_value', 'demand_value']:
            node = nodes['APDC_eco_' + suffix]
            x = int(node.get('position').val('x'))
            ranges = []
            for value in [number + unit for number in samples for unit in UNITS]:
                advance, ink = bounds(value, node.val('font'), chinese)
                origin = x + (int(node.val('maxWidth')) - advance[0]) / 2
                ranges.append([origin + ink[0][0], origin + ink[0][1]])
            rectangles.append([min(a for a, _ in ranges), max(b for _, b in ranges)])
        gaps['chinese' if chinese else 'base_font'] = {
            'ink_ranges_px': rectangles, 'gap_px': rectangles[1][0] - rectangles[0][1]}
    report['supply_demand_columns'] = gaps
    report['supply_demand_gap_px'] = min(row['gap_px'] for row in gaps.values())
    assert report['supply_demand_gap_px'] > 0, gaps
    OUT.mkdir(exist_ok=True)
    (OUT / 'font-fit-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    assert not report['failures'], report['failures'][:8]
    print('PASS:', len(report['fields']), 'numeric fields;', sum(v['cases'] for v in report['fields'].values()), 'font-fit cases; supply/demand gap', report['supply_demand_gap_px'], 'px')


if __name__ == '__main__':
    run()
