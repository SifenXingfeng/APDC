"""Reproduce native civilian availability without bypassing UI enable checks."""
import datetime
import shutil
from pathlib import Path
import sys

from common import ROOT


def build():
    sys.path.insert(0, str(ROOT / 'tools/performance'))
    import prepare_runtime
    profile = Path('D:/APDC_FactoryProbe_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
    prepare_runtime.QA = profile
    prepare_runtime.prepare(toolpack=True)
    driver = profile / 'driver'
    if '--baseline' in sys.argv or '--original-allocation' in sys.argv:
        baseline = ROOT.parent / '.codex_backups/APDC/20261023-160739-economy-panel-fixes/original'
        files = ['common/dynamic_modifiers/APDC_economy_dynamic_modifiers.txt']
        if '--baseline' in sys.argv:
            files.append('common/ideas/_economic.txt')
        for rel in files:
            target = driver / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(baseline / rel, target)
    (driver / 'common/defines/zzzz_APDC_performance_qa.lua').write_text(
        'NDefines.NGame.GAME_SPEED_SECONDS = { 0.1, 0.1, 0.1, 0.1, 0.0 }\n', 'utf-8')
    effects = driver / 'common/scripted_effects'
    effects.mkdir(parents=True)
    effects.joinpath('APDC_factory_probe.txt').write_text('''QA_factory_log = {
set_temp_variable = { QA_expected = modifier@consumer_goods_expected_value }
set_temp_variable = { QA_factor = modifier@consumer_goods_factor }
set_temp_variable = { QA_use = modifier@civilian_factory_use }
log = "APDC_FACTORY country=[THIS.GetTag] date=[GetDateText] total=[?num_of_civilian_factories] available=[?num_of_available_civilian_factories] projects=[?num_of_civilian_factories_available_for_projects] expected=[?QA_expected] factor=[?QA_factor] use=[?QA_use] public=[?APDC_eco_public_civ] limit=[?APDC_eco_public_available]"
if = { limit = { num_of_available_civilian_factories > 0 } log = "APDC_FACTORY native_available_trigger_POSITIVE" } else = { log = "APDC_FACTORY native_available_trigger_ZERO" }
if = { limit = { num_of_civilian_factories_available_for_projects > 0 } log = "APDC_FACTORY native_projects_trigger_POSITIVE" } else = { log = "APDC_FACTORY native_projects_trigger_ZERO" }
}
''', 'utf-8')
    (driver / 'common/dynamic_modifiers').mkdir(parents=True, exist_ok=True)
    (driver / 'common/dynamic_modifiers/APDC_factory_probe.txt').write_text('''QA_force_zero_consumer_goods = {
enable = { always = yes }
consumer_goods_expected_value = -1
}
''', 'utf-8')
    (driver / 'common/on_actions/zzzz_APDC_performance_qa.txt').write_text('''on_actions = {
on_daily_GER = { effect = {
QA_factory_log = yes
if = { limit = { NOT = { has_country_flag = QA_factory_stage1 } }
 set_country_flag = QA_factory_stage1
 remove_dynamic_modifier = { modifier = APDC_eco_allocation }
 add_dynamic_modifier = { modifier = QA_force_zero_consumer_goods }
 log = "APDC_FACTORY stage1_force_zero_expected"
} else_if = { limit = { NOT = { has_country_flag = QA_factory_stage2 } }
 set_country_flag = QA_factory_stage2
 log = "APDC_FACTORY stage2_remove_allocation"
} else_if = { limit = { NOT = { has_country_flag = QA_factory_stage3 } }
 set_country_flag = QA_factory_stage3
 log = "APDC_FACTORY stage3_no_allocation"
}
} }
}
''', 'utf-8')
    (ROOT / 'docs/economy/20261023-panel-regressions/factory-probe-profile.txt').write_text(str(profile), 'utf-8')
    print(profile)


if __name__ == '__main__':
    build()
