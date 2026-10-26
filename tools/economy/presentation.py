"""Economy presentation only: source-document colours and direct source tooltips.

No settlement, country enumeration or construction effects belong here.
"""
import json
import re
import zipfile
from lxml import etree

from common import ROOT, WORK, parse, patches, write

RUBLE = '£APDC_ruble_texticon£'


def document_colours():
    from build_data import SOURCE
    with zipfile.ZipFile(SOURCE) as archive:
        document = etree.fromstring(archive.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    colours = {}
    for paragraph in document.xpath('//w:body/w:p', namespaces=ns):
        line = ''.join(paragraph.xpath('.//w:t/text()', namespaces=ns))
        if '：' not in line:
            continue
        numeric = []
        for run in paragraph.xpath('./w:r', namespaces=ns):
            value = ''.join(run.xpath('.//w:t/text()', namespaces=ns))
            if re.search(r'\d', value):
                colour = run.xpath('./w:rPr/w:color/@w:val', namespaces=ns)
                numeric.append({'FF0000': 'R', '00B050': 'G'}.get(colour[0].upper() if colour else '', 'Y'))
        if numeric:
            assert len(set(numeric)) == 1, (line, numeric)
            if line in colours:
                assert colours[line] == numeric[0], line
            colours[line] = numeric[0]
    return colours


def descriptions(data):
    colours = document_colours()
    result = {}
    for group, values in data.items():
        for level, entry in enumerate(values['entries'], 1):
            lines = []
            for source in entry['source']:
                attr, value = source.split('：', 1)
                colour = colours[source]
                lines.append(attr + '：§' + colour + value.replace('₽', RUBLE) + '§!')
            eid = f'APDC_eco_{group}_{level}'
            result[eid + '_desc'] = '\\n'.join(lines) or '无额外修正'
            result[eid + '_ui_tip'] = '§Y' + entry['name'] + '§!\\n\\n' + result[eid + '_desc']
    return result


def patch_laws_and_descriptions():
    """Apply only presentation changes; preserve every existing modifier."""
    data = json.loads((WORK / 'design_data.json').read_text('utf-8'))
    path = ROOT / 'common/ideas/APDC_economy_laws.txt'
    raw = path.read_text('utf-8'); edits = []
    for category in parse(raw)[0].children:
        if category.key == 'hidden_ideas':
            continue
        for idea in category.children:
            if idea.value is not None:
                continue
            available = idea.get('available')
            edits.append((available.value_start, available.value_end, '{ has_idea = ' + idea.key + ' }'))
    write(path.relative_to(ROOT), patches(raw, edits))
    entries = descriptions(data)
    for language in ['simp_chinese', 'english']:
        path = ROOT / f'localisation/{language}/APDC_economy_l_{language}.yml'
        raw = path.read_text('utf-8-sig')
        for key, value in entries.items():
            line = f' {key}:0 "{value}"'
            pattern = r'^ ' + re.escape(key) + r':0 .*?$'
            if re.search(pattern, raw, flags=re.M):
                raw = re.sub(pattern, lambda _: line, raw, flags=re.M)
            else:
                raw += line + '\n'
        write(path.relative_to(ROOT), raw, True)



from direct_sources import augment


if __name__ == '__main__':
    patch_laws_and_descriptions()
