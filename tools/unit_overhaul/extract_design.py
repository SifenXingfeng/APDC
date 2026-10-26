"""Read-only OOXML extraction of the unit section; never alters the design DOCX."""
from pathlib import Path
from hashlib import sha256
import json
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(r'D:\Desktop\全组营级单位汇总.docx')
OUT = ROOT / 'art_source/unit_overhaul/design'

def extract():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = Document(SOURCE)
    units = []
    current = None
    section = ''
    for element in doc.element.body:
        if element.tag.endswith('}p'):
            p = Paragraph(element, doc)
            text = p.text.strip()
            if '德国DEMO' in text:
                break
            if re.match(r'^\*{1,3}[^*]', text):
                current = {'index': len(units)+1, 'title': text, 'section': section,
                           'paragraphs': [], 'tables': [], 'images': []}
                units.append(current)
            elif text.endswith((':', '：')) and not text.startswith(('装备', '内部')) and not current:
                section = text
            elif re.match(r'^(步兵单位|装甲单位|自动化单位|炮兵单位|支援连单位|团级支援)', text):
                section = text
                current = None
            if current is not None:
                if text:
                    current['paragraphs'].append(text)
                for blip in element.xpath('.//a:blip'):
                    rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                    if rid:
                        part = doc.part.related_parts[rid]
                        name = f'{current["index"]:02d}_{Path(str(part.partname)).name}'
                        (OUT/name).write_bytes(part.blob)
                        current['images'].append(name)
        elif element.tag.endswith('}tbl') and current is not None:
            table = Table(element, doc)
            rows = [[cell.text for cell in row.cells] for row in table.rows]
            if rows and any('营组-列' in c for c in rows[0]):
                break
            current['tables'].append(rows)
    # No empty accidental header records; require both summary and field table.
    assert all(len(u['tables']) == 2 for u in units), [(u['index'], u['title'], len(u['tables'])) for u in units if len(u['tables']) != 2]
    data = {'source': str(SOURCE), 'source_sha256': sha256(SOURCE.read_bytes()).hexdigest(), 'units': units}
    (OUT/'units_source.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = []
    for u in units:
        lines.append(f'\n[{u["index"]:02d}] {u["title"]} [{u["section"]}] icons={u["images"]}')
        lines += u['paragraphs'][1:]
        for row in u['tables'][1][1:]:
            lines.append(row[1].splitlines()[-1] + ' = ' + row[2].replace('\n',' / '))
    (OUT/'单位原始字段.txt').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'units': len(units), 'icons': sum(len(u['images']) for u in units), 'sha256': data['source_sha256']}, ensure_ascii=False))

if __name__ == '__main__':
    extract()
