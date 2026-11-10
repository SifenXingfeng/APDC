"""Prepare/verify a private GER scenario for native special bills; never launch the game."""
import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from common import ROOT, PARTIES, block, iff

REPORT = ROOT / 'docs/parliament/20261110-scripted-special-bills'
DEFAULT_PROFILE = Path.home() / '.codex/tmp/APDC_CountryQA_20261028_final/parliament_native_20261110'


def put(path, text, bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8-sig' if bom else 'utf-8')


def api(name, **args):
    return ''.join(f'set_temp_variable = {{ apdc_parl_arg_{key} = {value} }}\n' for key, value in args.items()) + f'apdc_parl_{name} = yes\n'


def check(label, condition):
    return iff(condition, f'log = "APDC_SPECIAL_QA PASS {label}"\n', f'log = "APDC_SPECIAL_QA FAIL {label}"\n')


def cv(key, value, operator='='):
    return f'check_variable = {{ {key} {operator} {value} }}'


def provider(key, ident, setup, submitted='', passed='', failed=''):
    return (block(f'apdc_parl_bill_{ident}_key', f'set_temp_variable = {{ apdc_parl_arg_KEY = token:{key} }}\n') +
            block(key + '_unlock', api('unlock_special_bill', ID=ident)) +
            block(key + '_setup', setup) + block(key + '_on_submit', submitted) +
            block(key + '_on_pass', passed) + block(key + '_on_fail', failed))


def prepare(profile):
    REPORT.mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, exist_ok=True)
    driver = profile / 'driver'
    descriptor = (ROOT / 'descriptor.mod').read_text('utf-8-sig')
    descriptor = re.sub(r'^path=.*$', 'path="' + ROOT.as_posix() + '"', descriptor, flags=re.M)
    put(profile / 'mod/APDC.mod', descriptor)
    put(profile / 'mod/APDC_NativeBillsQA.mod', 'name="APDC native special bill QA"\npath="' + driver.as_posix() + '"\ndependencies={ "少女前线-APDC" }\nsupported_version="1.19.*"\n')
    user = Path.home() / 'Documents/Paradox Interactive/Hearts of Iron IV'
    dlc = json.loads((user / 'dlc_load.json').read_text('utf-8-sig'))
    put(profile / 'dlc_load.json', json.dumps({'enabled_mods': ['mod/APDC.mod', 'mod/APDC_NativeBillsQA.mod'], 'disabled_dlcs': dlc.get('disabled_dlcs', [])}))
    put(profile / 'settings.txt', 'language="l_simp_chinese"\ngraphics={ size={ x=1920 y=1080 } min_gui={ x=1280 y=720 } gui_scale=1.0 fullScreen=no borderless=no shadows=no multi_sampling=0 maxanisotropy=0 vsync=no }\nmaster_volume=0\nmusic_volume=0\nsound_fx_volume=0\nsave_as_binary=no\nautosave="MONTHLY"\n')
    put(profile / 'pdx_settings.txt', '"Graphics"={ "display_mode"={ value="windowed" version=0 } "windowed_resolution"={ value="1920x1080" version=0 } "renderer"={ value="dx11" version=0 } "vsync"={ enabled=no version=0 } }\n"System"={ "language"={ value="l_simp_chinese" version=0 } }\n')
    put(driver / 'common/defines/zzzz_apdc_special_qa.lua', 'NDefines.NGame.GAME_SPEED_SECONDS = { 0.05, 0.05, 0.05, 0.05, 0.0 }\n')
    one, two, three = ['qa_special_' + word for word in ('one', 'two', 'three')]
    setup_one = ('set_temp_variable = { apdc_parl_arg_COST = 100 }\n' +
                 iff('has_country_flag = qa_special_cost_raised', 'set_temp_variable = { apdc_parl_arg_COST = 200 }\n') +
                 iff('has_country_flag = qa_special_visible NOT = { has_country_flag = qa_special_one_passed }',
                     'apdc_parl_show_special_bill = yes\n' + iff('has_country_flag = qa_special_available', 'apdc_parl_allow_special_bill = yes\n')))
    contents = [
        provider(one, 10001, setup_one, 'add_to_variable = { qa_one_submit = 1 }\nqa_special_two_unlock = yes\n',
                 'add_to_variable = { qa_one_pass = 1 }\nset_country_flag = qa_special_one_passed\n', 'add_to_variable = { qa_one_fail = 1 }\n'),
        provider(two, 10002, 'apdc_parl_show_special_bill = yes\napdc_parl_allow_special_bill = yes\n',
                 'add_to_variable = { qa_two_submit = 1 }\n', 'add_to_variable = { qa_two_pass = 1 }\n', 'add_to_variable = { qa_two_fail = 1 }\n'),
        provider(three, 10003, iff('has_country_flag = qa_special_three_visible', 'apdc_parl_show_special_bill = yes\napdc_parl_allow_special_bill = yes\n'),
                 'add_to_variable = { qa_three_submit = 1 }\n', 'add_to_variable = { qa_three_pass = 1 }\n', 'add_to_variable = { qa_three_fail = 1 }\n'),
    ]
    # Three independently loaded content files, created after the core bridge.
    for number, content in enumerate(contents, 1):
        put(driver / f'common/scripted_effects/APDC_special_bills_QA_{number}.txt', content)
    tokens = [entry for key in (one, two, three, 'qa_special_legacy') for entry in (key, key + '_desc')]
    put(driver / 'common/synchronized_dynamic_tokens/APDC_special_bills_QA.txt', '\n'.join(tokens) + '\n')
    loc = 'l_simp_chinese:\n' + ''.join(f' {key}:0 "无编译测试法案{number}"\n {key}_desc:0 "原生脚本扩展验证"\n' for number, key in enumerate((one, two, three, 'qa_special_legacy'), 1))
    put(driver / 'localisation/simp_chinese/APDC_special_bills_QA_l_simp_chinese.yml', loc, True)
    hooks = ''.join(block('apdc_parl_special_' + phase + '_hook', 'add_to_variable = { qa_legacy_' + phase + ' = 1 }\n') for phase in ('submitted', 'passed', 'failed'))
    put(driver / 'common/scripted_effects/apdc_parliament_story_hooks.txt', hooks)
    run = 'set_political_power = 2000\napdc_parl_enact_political_system_1 = yes\n'
    run += ''.join(f'set_variable = {{ qa_{bill}_{phase} = 0 }}\n' for bill in ('one', 'two', 'three') for phase in ('submit', 'pass', 'fail'))
    run += 'qa_special_one_unlock = yes\nqa_special_one_unlock = yes\n'
    run += check('duplicate_unlock_has_one_stable_id', cv('apdc_parl_scripted_special_ids^num', 1) + ' ' + cv('apdc_parl_scripted_special_ids^0', 10001))
    run += check('invisible_bill_is_not_listed', cv('apdc_parl_special_ids^num', 0))
    run += 'set_country_flag = qa_special_visible\napdc_parl_refresh_special_catalogue = yes\n'
    run += check('visible_but_unavailable', cv('apdc_parl_special_ids^0', 10001) + ' ' + cv('apdc_parl_special_enabled^0', 0) + ' ' + cv('apdc_parl_special_costs^0', 100))
    run += 'set_variable = { apdc_parl_selected_special_index = 0 }\napdc_parl_submit_special_bill = yes\n'
    run += check('disabled_bill_cannot_submit', cv('apdc_parl_agenda', 0) + ' ' + cv('qa_one_submit', 0))
    run += 'set_country_flag = qa_special_available\nset_country_flag = qa_special_cost_raised\napdc_parl_refresh_special_catalogue = yes\n'
    run += check('metadata_upsert_updates_price_and_availability', cv('apdc_parl_special_costs^0', 200) + ' ' + cv('apdc_parl_special_enabled^0', 1) + ' ' + cv('apdc_parl_special_ids^num', 1))
    run += 'set_temp_variable = { qa_expected_name = token:qa_special_one }\nset_temp_variable = { qa_expected_desc = token:qa_special_one_desc }\n'
    run += check('native_name_and_description_tokens', cv('apdc_parl_special_names^0', 'qa_expected_name') + ' ' + cv('apdc_parl_special_descriptions^0', 'qa_expected_desc'))
    run += 'set_political_power = 199\napdc_parl_submit_special_bill = yes\n'
    run += check('insufficient_political_power_cannot_submit', cv('apdc_parl_agenda', 0) + ' ' + cv('qa_one_submit', 0))
    run += 'set_political_power = 2000\napdc_parl_submit_special_bill = yes\n'
    run += check('immediate_native_callbacks_once', cv('qa_one_submit', 1) + ' ' + cv('qa_one_pass', 1) + ' ' + cv('qa_one_fail', 0) + ' ' + cv('apdc_parl_last_passed_special_id', 10001))
    run += check('correct_cost_is_paid_before_callback', 'has_political_power > 1799 has_political_power < 1801')
    run += check('callback_unlocks_second_file_without_registry_edit', cv('apdc_parl_scripted_special_ids^num', 2) + ' ' + cv('apdc_parl_special_ids^num', 1) + ' ' + cv('apdc_parl_special_ids^0', 10002))
    run += 'apdc_parl_refresh_special_catalogue = yes\napdc_parl_refresh_special_catalogue = yes\n'
    run += check('catalogue_refresh_does_not_repeat_rewards', cv('qa_one_pass', 1) + ' ' + cv('apdc_parl_special_ids^num', 1))
    run += api('register_special_bill', ID=900001, NAME='token:qa_special_legacy', DESC='token:qa_special_legacy_desc', COST=0)
    run += 'set_variable = { qa_legacy_passed = 0 }\nset_variable = { apdc_parl_selected_special_index = 1 }\napdc_parl_submit_special_bill = yes\n'
    run += check('legacy_registration_and_hooks_still_work', cv('qa_legacy_passed', 1) + ' ' + cv('apdc_parl_last_passed_special_id', 900001) + ' ' + cv('qa_two_pass', 0))
    run += api('remove_special_bill', ID=900001)
    run += 'apdc_parl_enact_political_system_4 = yes\n' + ''.join(f'set_variable = {{ apdc_parl_seats_{party} = {500 if party == "socialism" else 0} }}\n' for party in PARTIES)
    run += 'set_variable = { apdc_parl_selected_special_index = 0 }\napdc_parl_submit_special_bill = yes\n'
    run += check('ordinary_review_captures_native_callback_key', cv('apdc_parl_agenda', 1) + ' ' + cv('apdc_parl_bill_target', 10002) + ' ' + cv('qa_two_submit', 1))
    run += api('lock_special_bill', ID=10002)
    run += check('withdrawn_bill_leaves_active_agenda_intact', cv('apdc_parl_special_ids^num', 0) + ' ' + cv('apdc_parl_agenda', 1))
    run += 'apdc_parl_fail_agenda = yes\n'
    run += check('withdrawn_bill_failure_callback_keeps_correct_key', cv('qa_two_fail', 1) + ' ' + cv('qa_two_pass', 0) + ' ' + cv('apdc_parl_last_failed_special_id', 10002))
    run += 'set_country_flag = qa_special_three_visible\nqa_special_three_unlock = yes\nset_variable = { apdc_parl_selected_special_index = 0 }\napdc_parl_submit_special_bill = yes\n'
    run += 'clr_country_flag = qa_special_three_visible\napdc_parl_refresh_special_catalogue = yes\n'
    run += check('hidden_inflight_bill_retains_name_and_id', cv('apdc_parl_special_ids^num', 0) + ' ' + cv('apdc_parl_bill_target', 10003) + ' ' + cv('qa_three_submit', 1) + ' ' + cv('apdc_parl_scripted_special_ids^num', 2))
    run += 'set_country_flag = qa_special_core_finished\nlog = "APDC_SPECIAL_QA CORE_COMPLETE"\n'
    put(driver / 'common/scripted_effects/APDC_special_bills_QA_core_tests.txt', block('qa_special_run_core_tests', run))
    day = 'add_to_variable = { qa_special_day = 1 }\n' + iff('NOT = { has_country_flag = qa_special_core_finished }', 'qa_special_run_core_tests = yes\n')
    day += iff(cv('qa_special_day', 35), check('actual_dates_advance_with_pending_bill', cv('apdc_parl_agenda', 1) + ' ' + cv('apdc_parl_bill_work', 0, '>')) + 'log = "APDC_SPECIAL_QA COMPLETE"\n')
    put(driver / 'common/on_actions/zzzzzz_APDC_special_bills_QA.txt', block('on_actions', 'on_daily_GER = { effect = { ' + day + ' } }'))
    meta = {'profile': str(profile), 'project': str(ROOT), 'driver': str(driver), 'core_bridge_sha256': hashlib.sha256((ROOT / 'common/scripted_effects/apdc_parliament_special_catalogue.txt').read_bytes()).hexdigest(), 'user_profile_modified': False, 'purpose': 'native special bill API QA'}
    put(profile / 'qa-meta.json', json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False))


def prepare_reload(profile):
    save = profile / 'save games/autosave.hoi4'
    assert save.is_file(), 'Need an actual autosave first'
    # Add another independent content/token file only after the actual save
    # exists. This tests adding content without rebuilding the core, including
    # preservation of previously saved token-backed callback keys.
    late = 'qa_added_later_bill'
    put(profile / 'driver/common/scripted_effects/AAA_special_bill_added_after_save.txt',
        provider(late, 10004, 'apdc_parl_show_special_bill = yes\napdc_parl_allow_special_bill = yes\n',
                 'add_to_variable = { qa_four_submit = 1 }\n', 'add_to_variable = { qa_four_pass = 1 }\n', 'add_to_variable = { qa_four_fail = 1 }\n'))
    put(profile / 'driver/common/synchronized_dynamic_tokens/AAA_special_bill_added_after_save.txt', late + '\n' + late + '_desc\n')
    put(profile / 'driver/localisation/simp_chinese/AAA_special_bill_added_after_save_l_simp_chinese.yml',
        'l_simp_chinese:\n ' + late + ':0 "读档前新增的第四条法案"\n ' + late + '_desc:0 "不修改核心或分发表"\n', True)
    body = 'set_temp_variable = { qa_id_format = 10003 }\nlog = "APDC_SPECIAL_QA ID_FORMAT default=[?qa_id_format] integer=[?qa_id_format|0] raw=[?qa_id_format|0..]"\n'
    body += check('reload_keeps_native_registry', cv('apdc_parl_scripted_special_ids^num', 2))
    body += check('reload_keeps_hidden_inflight_bill', cv('apdc_parl_agenda', 1) + ' ' + cv('apdc_parl_bill_target', 10003) + ' ' + cv('apdc_parl_special_ids^num', 0))
    body += check('reload_keeps_progress_and_callback_counts', cv('apdc_parl_bill_work', 0, '>') + ' ' + cv('qa_three_submit', 1) + ' ' + cv('qa_three_pass', 0))
    body += 'set_temp_variable = { qa_expected_key = token:qa_special_three }\n'
    body += check('saved_callback_key_rebound_after_new_content', cv('apdc_parl_scripted_active_key', 'qa_expected_key'))
    body += 'set_variable = { apdc_parl_bill_work = apdc_parl_bill_base_days }\napdc_parl_refresh = yes\napdc_parl_validate_agenda = yes\n'
    body += check('reloaded_native_callback_completes_once', cv('qa_three_pass', 1) + ' ' + cv('qa_three_fail', 0) + ' ' + cv('apdc_parl_last_passed_special_id', 10003))
    body += 'apdc_parl_refresh_special_catalogue = yes\napdc_parl_refresh_special_catalogue = yes\n'
    body += check('reloaded_reward_not_repeated', cv('qa_three_pass', 1) + ' ' + cv('apdc_parl_agenda', 0))
    body += 'apdc_parl_enact_political_system_1 = yes\nqa_added_later_bill_unlock = yes\nset_variable = { apdc_parl_selected_special_index = 0 }\napdc_parl_submit_special_bill = yes\n'
    body += check('new_file_works_without_core_recompilation', cv('qa_four_submit', 1) + ' ' + cv('qa_four_pass', 1) + ' ' + cv('apdc_parl_last_passed_special_id', 10004))
    body += check('new_bill_does_not_replay_other_callbacks', cv('qa_three_pass', 1) + ' ' + cv('qa_one_pass', 1) + ' ' + cv('qa_two_fail', 1))
    body += 'apdc_parl_finish_agenda = yes\n'
    body += ''.join('clear_array = ' + name + '\n' for name in ['apdc_parl_scripted_special_ids','apdc_parl_scripted_special_keys','apdc_parl_special_ids','apdc_parl_special_names','apdc_parl_special_descriptions','apdc_parl_special_costs','apdc_parl_special_enabled'])
    body += ''.join('clr_country_flag = ' + flag + '\n' for flag in ['qa_special_visible','qa_special_available','qa_special_cost_raised','qa_special_one_passed','qa_special_three_visible'])
    body += 'log = "APDC_SPECIAL_QA REPLAY_CORE_WITH_STABLE_ID_ROUTER"\nqa_special_run_core_tests = yes\n'
    body += 'set_country_flag = qa_special_reload_checked\nlog = "APDC_SPECIAL_QA RELOAD_COMPLETE"\n'
    day = iff('NOT = { has_country_flag = qa_special_reload_checked }', body)
    put(profile / 'driver/common/on_actions/zzzzzz_APDC_special_bills_QA.txt', block('on_actions', 'on_daily_GER = { effect = { ' + day + ' } }'))
    put(profile / 'continue_game.json', json.dumps({'title': 'Native bill persistence QA', 'desc': '',
        'date': datetime.fromtimestamp(save.stat().st_mtime).ctime() + '\n',
        'filename': 'autosave.hoi4', 'is_remote': False}))
    print(json.dumps({'prepared_reload': True, 'save': str(save), 'save_sha256': hashlib.sha256(save.read_bytes()).hexdigest()}))


def verify(profile, phase):
    game = (profile / 'logs/game.log').read_text('utf-8-sig', errors='replace')
    errors = (profile / 'logs/error.log').read_text('utf-8-sig', errors='replace')
    passed = re.findall(r'APDC_SPECIAL_QA PASS (\w+)', game)
    failed = re.findall(r'APDC_SPECIAL_QA FAIL (\w+)', game)
    relevant = [line for line in errors.splitlines() if re.search(r'apdc_parl|parliament|qa_special|qa_added|APDC_special_bills|meta effect', line, re.I)]
    marker = 'APDC_SPECIAL_QA RELOAD_COMPLETE' if phase == 'reload' else 'APDC_SPECIAL_QA CORE_COMPLETE'
    report = {'status': 'passed' if marker in game and not failed and not relevant else 'failed', 'phase': phase,
              'passed': passed, 'failed': failed, 'related_engine_errors': relevant, 'marker_found': marker in game,
              'actual_dlc': [line for line in (profile / 'logs/system.log').read_text('utf-8-sig', errors='replace').splitlines() if 'Active DLC:' in line]}
    report['distinct_assertions'] = len(set(passed))
    if report['distinct_assertions'] < (24 if phase == 'reload' else 16):
        report['status'] = 'failed'
    meta = json.loads((profile / 'qa-meta.json').read_text('utf-8'))
    report['core_bridge_unchanged'] = hashlib.sha256((ROOT / 'common/scripted_effects/apdc_parliament_special_catalogue.txt').read_bytes()).hexdigest() == meta['core_bridge_sha256']
    if not report['core_bridge_unchanged']:
        report['status'] = 'failed'
    if phase == 'initial':
        from audit import save_country
        save = profile / 'save games/autosave.hoi4'
        text = save.read_text('utf-8-sig')
        variables = save_country(text, 'GER').get('variables')
        report['save_date'] = re.search(r'^date="([^"]+)"', text, re.M).group(1)
        report['saved_pending_bill'] = variables.val('apdc_parl_bill_target')
        report['saved_progress'] = variables.val('apdc_parl_bill_work')
        if variables.val('apdc_parl_agenda') != '1' or variables.val('apdc_parl_bill_target') != '10003' or float(report['saved_progress']) <= 0:
            report['status'] = 'failed'
    REPORT.mkdir(parents=True, exist_ok=True)
    put(REPORT / (phase + '-verification.json'), json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(report['status'] != 'passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--mode', choices=('prepare', 'reload', 'verify', 'verify-reload'), default='prepare')
    args = parser.parse_args()
    if args.mode == 'prepare': prepare(args.profile)
    elif args.mode == 'reload': prepare_reload(args.profile)
    else: verify(args.profile, 'reload' if args.mode == 'verify-reload' else 'initial')
