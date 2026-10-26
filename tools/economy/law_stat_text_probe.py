"""Isolated experiment: replace the native consumer-goods statistic's text.

This checks localization and country scope. It does not emulate the native
idea-row controller, and must not be described as a visual/native-row test.
"""
import datetime
import hashlib
import json
from pathlib import Path
import sys

from common import ROOT


def build():
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = ROOT / 'docs/economy/20261023-law-stat-text'
    out.mkdir(parents=True, exist_ok=True)
    backup = ROOT.parent / '.codex_backups/APDC' / (now.replace('_', '-') + '-law-stat-text')
    backup.mkdir(parents=True)
    rels = ['interface/countrypoliticsview.gui', 'common/ideas/_economic.txt',
            'common/scripted_effects/APDC_economy_backend.txt',
            'common/dynamic_modifiers/APDC_economy_dynamic_modifiers.txt',
            'localisation/replace/zzzz_APDC_economy_display_l_simp_chinese.yml',
            'localisation/replace/zzzz_APDC_economy_display_l_english.yml']
    hashes = {}
    for rel in rels:
        raw = (ROOT / rel).read_bytes()
        p = backup / 'original' / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        hashes[rel] = hashlib.sha256(raw).hexdigest()
    (backup / 'sha256.json').write_text(json.dumps(hashes, indent=2), 'utf-8')
    (out / 'backup.txt').write_text(str(backup), 'utf-8')
    (out / 'project-before.json').write_text(json.dumps(hashes, indent=2), 'utf-8')
    sys.path.insert(0, str(ROOT / 'tools/performance'))
    import prepare_runtime
    qa = Path('D:/APDC_LawStatTextQA_' + now)
    prepare_runtime.QA = qa
    prepare_runtime.prepare(toolpack=True)
    driver = qa / 'driver'
    (driver / 'common/defines/zzzz_APDC_performance_qa.lua').write_text(
        'NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.0 }\n', 'utf-8')
    replacement = ' £consumer_goods_texticon£  [?modifier@APDC_eco_population_base|Y2]'
    locdir = driver / 'localisation/replace'
    locdir.mkdir(parents=True)
    for language in ['simp_chinese', 'english']:
        (locdir / ('zzzz_APDC_economy_display_l_' + language + '.yml')).write_text(
            'l_' + language + ':\n POLITICS_IDEA_STAT_CONSUMER_GOODS:0 "' + replacement + '"\n', 'utf-8-sig')
    folder = driver / 'common/scripted_localisation'
    folder.mkdir(parents=True)
    (folder / 'APDC_law_stat_text_probe.txt').write_text('''defined_text = {
name = APDCLawStatTextProbe
text = { localization_key = POLITICS_IDEA_STAT_CONSUMER_GOODS }
}
''', 'utf-8')
    folder = driver / 'common/scripted_effects'
    folder.mkdir(parents=True)
    laws = ['undisturbed_isolation', 'isolation', 'civilian_economy',
            'low_economic_mobilisation', 'partial_economic_mobilisation',
            'war_economy', 'tot_economic_mobilisation']
    effects = ''
    for active in ['civilian_economy', 'tot_economic_mobilisation']:
        body = ''.join('remove_ideas = ' + k + '\n' for k in laws)
        body += 'add_ideas = ' + active + '\nAPDC_eco_refresh_policies = yes\nAPDC_eco_refresh_current_supply = yes\n'
        # "candidate" is a diagnostic label, not a fabricated idea scope.
        for candidate, expected in [('civilian_economy', '1.00'), ('tot_economic_mobilisation', '0.40')]:
            body += 'log = "APDC_STAT_TEXT active=' + active + ' candidate_label=' + candidate + ' wanted=' + expected + ' rendered=[APDCLawStatTextProbe]"\n'
        body += 'log = "APDC_STAT_FACTORY active=' + active + ' all=[?num_of_civilian_factories] projects=[?num_of_civilian_factories_available_for_projects] allocated=[?APDC_eco_public_civ]"\n'
        effects += 'QA_stat_' + active + ' = {\n' + body + '}\n'
    (folder / 'APDC_law_stat_text_probe.txt').write_text(effects, 'utf-8')
    (driver / 'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('''on_actions = { on_daily_GER = { effect = {
if = { limit = { NOT = { has_country_flag = QA_stat_civilian } }
 set_country_flag = QA_stat_civilian QA_stat_civilian_economy = yes
} else_if = { limit = { NOT = { has_country_flag = QA_stat_total } }
 set_country_flag = QA_stat_total QA_stat_tot_economic_mobilisation = yes
} else_if = { limit = { NOT = { has_country_flag = QA_stat_restored } }
 set_country_flag = QA_stat_restored QA_stat_civilian_economy = yes
}
log = "APDC_STAT_DAY date=[GetDateText]"
} } }
''', 'utf-8')
    userdir = Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
    names = ['dlc_load.json', 'settings.txt', 'continue_game.json', 'save games/autosave.hoi4']
    (out / 'user-before.json').write_text(json.dumps({str(userdir/n): hashlib.sha256((userdir/n).read_bytes()).hexdigest() for n in names}, indent=2), 'utf-8')
    (out / 'profile.txt').write_text(str(qa), 'utf-8')
    print(qa)


if __name__ == '__main__':
    build()
