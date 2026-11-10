"""Import only the agreed law catalogue and existing cabinet source records."""
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import re
from common import *

HEADINGS=['人形权利法案','感染者权利法案','妇女权利法案','遗迹技术法案','经济体制','政治体制']
KEYS=['doll_rights','infected_rights','women_rights','relic_technology','economic_system','political_system']


def import_sources():
    policy=json.loads(read('docs/parliament/20261107-design/opening_policy.json'))
    source=SOURCE/'documents/laws.docx'
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with ZipFile(source) as z:
        root=ET.fromstring(z.read('word/document.xml'))
        lines=[''.join(n.text or '' for n in el.findall('.//w:t',ns)).strip() for el in root.find('w:body',ns)]
    option_names={**policy['law_options'],'economic_system':list(policy['economic_names'].values()),'political_system':[v['name'] for v in policy['regimes'].values()]}
    groups=[];group=None;option=None
    for line in lines:
        if not line:continue
        if line in HEADINGS:
            key=KEYS[HEADINGS.index(line)]
            group={'id':HEADINGS.index(line)+1,'key':key,'name':line,'options':[]}
            groups.append(group);option=None
        elif group and line in option_names[group['key']]:
            option={'id':len(group['options'])+1,'name':line,'effects':[]};group['options'].append(option)
        elif option and not line.startswith('LOGO'):
            if group['key']=='infected_rights':line=line.replace('每月人力：','每月人口：')
            if group['key']=='relic_technology':line=line.replace('每周人力：','每月人口：')
            option['effects'].append(line)
    assert [len(g['options']) for g in groups]==[7,6,5,6,10,9]
    # Keep an editable catalogue; later builds never reread a changed source
    # document unless --import-data is explicitly requested.
    json_write('tools/parliament/data/laws.json',{'schema_version':1,'source':source.relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'user_corrections':['2026-11-07 感染者每月人力与遗迹每周人力均指每月人口增长率修正；后者为笔误。'],'groups':groups})
    json_write('tools/parliament/data/regimes.json',policy['regimes'])
    draft=json.loads(read('docs/parliament/20261107-design/initial_setup_draft.json'))
    json_write('tools/parliament/data/opening_countries.json',draft['countries'])
    for rel in ['interface/APDC_cabinet.gui','common/scripted_guis/APDC_cabinet_scripted_gui.txt','common/scripted_effects/APDC_cabinet_scripted_effects.txt','common/scripted_triggers/APDC_cabinet_scripted_triggers.txt','common/scripted_localisation/APDC_cabinet_scripted_localisation.txt','common/scripted_triggers/APDC_cabinet_group_visibility_triggers.txt']:
        dest='tools/parliament/legacy/'+Path(rel).name
        if not (ROOT/dest).exists():
            write(dest,(ROOT/rel).read_bytes())
    input_dir=BACKUP if False else None
    return groups
