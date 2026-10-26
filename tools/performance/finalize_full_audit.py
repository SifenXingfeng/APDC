"""Record the completed, individually reviewed cleanup batch; never mutate game data.

The old text-reference closure is evidence of what was deleted, not evidence that
deleting it was safe. Engine hooks, automatic selectors, player-selectable pools,
native localisation callers and dependencies are reviewed separately here.
"""
from pathlib import Path
import collections
import hashlib
import json
import re
import sys

from full_regression_audit import ROOT, OUT, load, source_before
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse


def clean(path):
    return path.read_bytes().decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def definitions(folder):
    result = {}
    for path in (ROOT / folder).rglob('*.txt'):
        for node in parse(clean(path)):
            if folder == 'common/ideas':
                if node.key != 'ideas':
                    continue
                items = [item for category in node.children for item in category.children]
            elif folder == 'common/country_leader':
                items = node.children if node.key == 'leader_traits' else []
            else:
                items = [node]
            for item in items:
                if item.value is None:
                    result.setdefault(item.key, []).append(path.relative_to(ROOT).as_posix())
    return result


def inactive_disposition(folder, rel, key, old_categories):
    if folder == 'common/ideas':
        category = old_categories.get((rel, key))
        if category in ['political_advisor', 'theorist', 'army_chief', 'navy_chief',
                        'air_chief', 'high_command']:
            return 'Discarded WW2 personal-advisor pool; APDC uses character slots and its own cabinet characters.'
        if category in ['tank_manufacturer', 'naval_manufacturer', 'aircraft_manufacturer',
                        'materiel_manufacturer', 'industrial_concern']:
            return 'Company restricted to an unregistered native identity; eligible APDC company pools restored separately.'
        return 'Inactive imported national/event spirit; no retained APDC entry point. Active selectable laws and project costs preserved.'
    if folder == 'common/country_leader':
        return 'Trait of discarded WW2 people or national story; all dependencies of active APDC characters and recovered companies preserved.'
    if folder == 'common/bop':
        return 'Discarded native national balance-of-power scenario; APDC has no corresponding national focus or event entry point.'
    if folder == 'common/dynamic_modifiers':
        return 'Inactive native national-story modifier; actual project accident and active APDC modifier dependencies preserved.'
    if rel.endswith('/zz_debug_effects.txt') or key in ['lerp', 'test_game_reached_1948']:
        return 'Native developer/AI-test helper, not a normal APDC gameplay entry point.'
    if key.startswith('DIPLOMACY_'):
        return 'Only discarded WW2 treaty/protectorate restrictions; generic engine diplomacy callbacks restored and guarded separately.'
    return 'Unused helper of discarded WW2 plots, old unit variants or developer utilities; retained callers, engine callback names and automatic selectors independently audited.'


def file_review(rel, reasons):
    if rel.startswith('gfx/flags/'):
        return 'Flag format/fallback review; existing visible pixels preserved, explicit ideology variants retained.'
    if rel.startswith('localisation/'):
        return 'Localisation precedence/key-coverage review; 45,345 deduplicated rows still defined, authored replacement values retained.'
    if rel.startswith('history/countries/'):
        return 'Registered APDC identities, histories and people retained; only 37 unregistered native histories removed, stale tech grants adapted.'
    if rel.startswith(('common/units/', 'gfx/interface/equipmentdesigner/')):
        return 'Approved APDC roster reviewed; 82 authored unit definitions retained, doctrine compatibility IDs kept non-playable, obsolete native art/roster references removed.'
    if rel.startswith(('interface/', 'gfx/', 'music/')):
        return 'UI/assets/music review; geometry and source pixels checked separately, generic playback conditions restored, no map-style changes.'
    if rel.startswith('common/technologies/'):
        return 'APDC technology-tree review; authored rewards retained, duplicate night_vision3 keeps final authored value, retired native trees remain excluded.'
    if rel.startswith(('common/doctrines/', 'common/factions/', 'common/special_projects/', 'common/raids/')):
        return 'Generic gameplay/selection review; supported goals, templates, projects and dependencies restored; branches requiring absent platforms or WW2 national plots remain removed.'
    if rel.startswith(('common/scripted_', 'common/ideas/', 'common/dynamic_modifiers/', 'common/country_leader/', 'common/bop/')):
        return 'Definition and implicit-caller review; see complete deleted-definition dispositions plus explicit restorations, not the old reference-closure assumption.'
    if rel.startswith('common/defines/'):
        return 'Obsolete full native table replaced by seven actual APDC differences; unsupported fields removed, current engine defaults inherited.'
    if rel.startswith(('tools/', 'docs/')):
        return 'Maintenance/validation artifact, not gameplay deletion.'
    return 'Reviewed explicit field/reference compatibility repair against pre-cleanup bytes; authored content and effects retained.'


def finish():
    inventory = load(OUT / 'complete-inventory.json')
    restorations = load(OUT / 'restorations.json')
    bypath = collections.defaultdict(list)
    for row in restorations:
        bypath[row['path']].append(row)
    weekly = {r['path'] for r in load(ROOT / 'docs/performance/20261023-weekly-economy/final-changes.json')}
    callbacks = {r['path'] for r in load(ROOT / 'docs/performance/20261023-core-regression/repairs.json')}
    reviews = []
    for rel in sorted(set(inventory) | set(bypath)):
        original = inventory.get(rel, {})
        current = ROOT / rel
        reviews.append({
            'path': rel,
            'pre_cleanup_source': original.get('before_source') or str(source_before(rel) or ''),
            'pre_cleanup_sha256': original.get('before_sha256'),
            'final_sha256': digest(current),
            'final_exists': current.exists(),
            'review': file_review(rel, original.get('reasons', [])),
            'original_cleanup_reasons': original.get('reasons', []),
            'restoration_reasons': list(dict.fromkeys(r['reason'] for r in bypath.get(rel, []))),
            'authorized_weekly_optimization_preserved': rel in weekly,
            'previous_core_callback_repair': rel in callbacks,
        })
    (OUT / 'file-dispositions.json').write_text(json.dumps(reviews, indent=2), 'utf-8')

    closure = load(ROOT / 'docs/performance/20261023/legacy_reference_closure.json')
    families = {'/'.join(row['path'].split('/')[:2]) for row in closure}
    active = {folder: definitions(folder) for folder in families}
    old_categories = {}
    for row in closure:
        if not row['path'].startswith('common/ideas/'):
            continue
        source = source_before(row['path'])
        raw = clean(source)
        try:
            original_nodes = parse(raw)
        except ValueError as exc:
            # These two original snapshots already lacked the final container
            # brace. Repair only the in-memory forensic view, never the source.
            assert row['path'] in ['common/ideas/persia.txt', 'common/ideas/switzerland.txt']
            assert str(exc) == 'Unclosed block'
            original_nodes = parse(raw + '\n}\n')
        for wrapper in original_nodes:
            for category in wrapper.children:
                for item in category.children:
                    old_categories[row['path'], item.key] = category.key
    deleted = []
    for row in closure:
        folder = '/'.join(row['path'].split('/')[:2])
        for key in row['removed']:
            found = active[folder].get(key, [])
            deleted.append({
                'original_file': row['path'], 'definition': key,
                'status': 'restored' if found else 'unrelated_legacy_removed',
                'final_definitions': found,
                'disposition': ('Restored with its required APDC-compatible dependencies.' if found else
                                inactive_disposition(folder, row['path'], key, old_categories)),
                'old_category': old_categories.get((row['path'], key)),
            })
    (OUT / 'deleted-definition-dispositions.json').write_text(json.dumps(deleted, indent=2), 'utf-8')

    backup = Path((OUT / 'backup.txt').read_text('utf-8').strip())
    oldhashes = load(backup / 'sha256.json')
    unexpected = [rel for rel, before in oldhashes.items()
                  if before != digest(ROOT / rel) and rel not in bypath]
    assert not unexpected, unexpected
    checks = load(OUT / 'final-verification.json')
    assert checks['project_or_unclassified_records'] == 0 and not checks['syntax_errors']
    assert not checks['state_history_changes']
    assert not load(OUT / 'restored-predicate-rescan.json')
    runtime = load(OUT / 'runtime-evidence.json')
    assert len(runtime['pass']) == 24 and not runtime['fail']
    preservation = load(OUT / 'preservation-verification.json')
    assert not preservation['missing_localisation_rows'] and not preservation['flag_pixel_changes']
    assert all(r['unchanged'] for r in load(OUT / 'user-files-after-runtime.json'))
    designers = load(OUT / 'designer-audit.json')
    names = load(OUT / 'division-name-audit.json')
    summary = {
        'original_cleanup_files': len(load(ROOT / 'docs/performance/20261023/final-changes.json')),
        'initial_full_audit_paths': len(inventory),
        'final_reviewed_paths': len(reviews),
        'restoration_paths_this_turn': len(bypath),
        'initial_pruned_definitions': len(deleted),
        'definition_dispositions': dict(collections.Counter(r['status'] for r in deleted)),
        'automatic_name_groups': sum(len(r['eligible_groups']) for r in names),
        'selectable_company_ideas': sum(len(r['restored']) for r in designers),
        'unexpected_changes_outside_restoration_manifest': unexpected,
        'final_runtime_date': runtime['date'],
        'assertions_passed': len(runtime['pass']),
        'project_error_records': checks['project_or_unclassified_records'],
        'syntax_files': checks['parsed_script_files'],
        'user_files_unchanged': True,
        'test_processes_closed': not runtime['process_cleanup']['still_running'] and not runtime['process_cleanup']['remaining_helpers'],
    }
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2), 'utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    finish()
