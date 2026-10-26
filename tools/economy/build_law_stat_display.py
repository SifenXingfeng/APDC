"""Fixed population coefficients in the native law list's unused traits field.

Native stats retain their consumer-goods icon and reserve the number's width.
Each economic idea supplies its own literal label, with no modifier attached.
"""
import json
from PIL import Image

from common import ROOT, block, effective_files, parse, patches, write


PREFIX = 'APDC_eco_population_display_'


def build():
    native = ROOT / 'common/ideas/_economic.txt'
    raw = native.read_text('utf-8-sig')
    economy = parse(raw)[0].get('economy')
    labels = {}
    edits = []
    for idea in economy.children:
        if not idea.children:
            continue
        modifier = idea.get('modifier')
        base = modifier.get('APDC_eco_population_base') if modifier else None
        # Mirrors the backend's default for the remaining legacy economy laws.
        value = float(base.value) if base and float(base.value) > 0 else 1.0
        trait = PREFIX + str(round(value * 100))
        labels[trait] = f'{value:.2f}'
        old = idea.get('traits')
        kept = [x.key for x in old.children if not x.key.startswith((PREFIX, 'APDC_eco_population_base_'))] if old else []
        text = '{ ' + ' '.join(kept + [trait]) + ' }'
        if old:
            edits.append((old.value_start, old.value_end, text))
        else:
            edits.append((idea.value_end - 1, idea.value_end - 1, '\ntraits = ' + text + '\n'))

    # The shared list template is safe to reuse only while other list-view
    # categories have no visible trait labels. The project's three markers
    # intentionally localize to empty strings in Chinese and English.
    allowed = {'science_idea', 'society_idea', 'poverty_idea'}
    for path in effective_files('common/ideas'):
        for top in parse(path.read_text('utf-8-sig')):
            if top.key != 'ideas':
                continue
            for category in top.children:
                view = category.get('use_list_view')
                if category.key == 'economy' or not view or view.value != 'yes':
                    continue
                for idea in category.children:
                    traits = idea.get('traits')
                    if traits:
                        unexpected = {t.key for t in traits.children} - allowed
                        if unexpected:
                            raise ValueError(f'Shared native list has additional trait text: {path.name}: {unexpected}')

    gui = ROOT / 'interface/countrypoliticsview.gui'
    with gui.open('r', encoding='utf-8', newline='') as handle:
        source = handle.read()
    row = next(n for n in parse(source)[0].children
               if n.get('name') and n.get('name').value.strip('"') == 'political_selectable_idea_entry_list')
    container = next(n for n in row.children
                     if n.get('name') and n.get('name').value.strip('"') == 'traits_container')
    label = next(n for n in container.children
                 if n.get('name') and n.get('name').value.strip('"') == 'traits')
    gui_edits = []
    for node, value in [(label.get('position').get('x'), '316'),
                        (label.get('position').get('y'), '32'),
                        (label.get('maxWidth'), '58'), (label.get('maxHeight'), '20')]:
        gui_edits.append((node.value_start, node.value_end, value))
    truncate = label.get('truncate')
    if truncate:
        gui_edits.append((truncate.value_start, truncate.value_end, 'no'))
    else:
        newline = '\r\n' if '\r\n' in source else '\n'
        gui_edits.append((label.value_end - 1, label.value_end - 1, 'truncate = no' + newline + '\t\t\t'))
    clipping = container.get('clipping')
    if clipping:
        gui_edits.append((clipping.value_start, clipping.value_end, 'no'))
    else:
        newline = '\r\n' if '\r\n' in source else '\n'
        gui_edits.append((container.value_end - 1, container.value_end - 1, 'clipping = no' + newline + '\t\t'))

    # All validation precedes mutations. Do not rebuild any economy formulas.
    write(native.relative_to(ROOT), patches(raw, edits))
    with gui.open('w', encoding='utf-8', newline='') as handle:
        handle.write(patches(source, gui_edits))
    write('common/country_leader/APDC_economy_population_traits.txt',
          block('leader_traits', ''.join(block(k, 'random = no') for k in sorted(labels))))
    asset = ROOT / 'gfx/interface/APDC/economy/population_coefficient_space.tga'
    asset.parent.mkdir(parents=True, exist_ok=True)
    # A fixed-width transparent text icon keeps the original coal/icon layout.
    Image.new('RGBA', (24, 20)).save(asset)
    write('interface/APDC_economy_population_stat.gfx', block('spriteTypes', block('spriteType',
          'name = "GFX_APDC_population_coefficient_space"\n'
          'texturefile = "gfx/interface/APDC/economy/population_coefficient_space.tga"\n'
          'legacy_lazy_load = no\nnoOfFrames = 1')))
    for language in ['simp_chinese', 'english']:
        values = ''.join(' ' + k + ':0 "§Y' + v + '§!"\n' for k, v in sorted(labels.items()))
        write('localisation/replace/zzzz_APDC_economy_display_l_' + language + '.yml',
              'l_' + language + ':\n'
              ' POLITICS_IDEA_STAT_CONSUMER_GOODS:0 " £consumer_goods_texticon£  £APDC_population_coefficient_space£"\n' + values, True)
    print('Fixed native law labels:', json.dumps(labels, ensure_ascii=False))


if __name__ == '__main__':
    build()
