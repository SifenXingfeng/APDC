"""Read current APDC sources and prepare a non-runtime parliament opening draft.

Only the explicitly supplied --output JSON is written. Existing output is
protected unless --replace-draft is supplied. This never modifies game history.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
from cw import parse


def read_nodes(path):
    return parse(path.read_text(encoding='utf-8-sig'))


def before_start(nodes, start):
    result = []
    for node in nodes:
        if re.fullmatch(r'\d{4}\.\d{1,2}\.\d{1,2}', node.key):
            if tuple(map(int, node.key.split('.'))) <= start:
                result.extend(before_start(node.children, start))
        else:
            result.append(node)
    return result


def condition(nodes, tag, party, subjects):
    values = []
    for node in nodes:
        if node.key in ('OR', 'AND', 'NOT'):
            child = [condition([n], tag, party, subjects) for n in node.children]
            values.append(any(child) if node.key == 'OR' else not any(child) if node.key == 'NOT' else all(child))
        elif node.key == 'tag':
            values.append(tag == node.value)
        elif node.key == 'has_government':
            values.append(party == node.value)
        elif node.key == 'is_subject':
            values.append((tag in subjects) == (node.value == 'yes'))
        elif node.key == 'always':
            values.append(node.value == 'yes')
        else:
            raise ValueError('Unmodelled initialization condition: ' + node.key)
    return all(values)


def build(policy):
    sources = {}
    def track(path):
        sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    registry = {}
    for path in sorted((ROOT / 'common/country_tags').glob('*.txt')):
        track(path)
        registry.update({n.key: n.value.strip('"') for n in read_nodes(path) if n.value is not None and re.fullmatch('[A-Z0-9]{3}', n.key)})
    start = (2060, 1, 1)
    histories = {}
    for path in sorted((ROOT / 'history/countries').glob('*.txt')):
        if path.name[:3] in registry:
            track(path)
            histories[path.name[:3]] = (path, before_start(read_nodes(path), start))
    assert set(histories) == set(registry), 'Registered identities missing history'
    parent = {}
    for path in sorted((ROOT / 'common/ideologies').glob('*.txt')):
        track(path)
        for outer in read_nodes(path):
            if outer.key != 'ideologies':
                continue
            for group in outer.children:
                types = group.get('types')
                if types:
                    parent.update({n.key: group.key for n in types.children})
    roles = {}
    for path in sorted((ROOT / 'common/characters').glob('*.txt')):
        track(path)
        for outer in read_nodes(path):
            if outer.key == 'characters':
                for character in outer.children:
                    roles[character.key] = [n.val('ideology') for n in character.children if n.key == 'country_leader']
    subjects = set()
    for _, nodes in histories.values():
        for node in nodes:
            if node.key in ('set_autonomy', 'puppet') and node.val('target'):
                subjects.add(node.val('target'))
    initial_path = ROOT / 'common/scripted_effects/APDC_economic_system_scripted_effects.txt'
    track(initial_path)
    economic_init = next(n for n in read_nodes(initial_path) if n.key == 'APDC_assign_initial_economic_system')
    territories_path = ROOT / 'tools/map_maintenance/baseline/initial_territories.json'
    track(territories_path)
    owner_counts = collections.Counter(v['owner'] for v in json.loads(territories_path.read_text(encoding='utf-8-sig')).values() if v.get('owner'))
    country_names = {}
    loc_paths = sorted((ROOT / 'localisation/simp_chinese').rglob('*.yml')) + sorted((ROOT / 'localisation/replace').glob('*simp_chinese.yml'))
    loc_pattern = re.compile(r'^\s*([A-Za-z0-9_.-]+):(?:-?\d+)?\s+"((?:\\.|[^"\\])*)"')
    for path in loc_paths:
        matched = False
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match = loc_pattern.match(line)
            if match and match[1].split('_')[0] in registry:
                country_names[match[1]] = match[2].replace('\\"', '"')
                matched = True
        if matched:
            track(path)
    entries = {}
    for tag, (path, nodes) in sorted(histories.items()):
        politics = {}
        for node in nodes:
            if node.key == 'set_politics':
                politics.update({n.key: n.value.strip('"') for n in node.children if n.value is not None})
        party = politics.get('ruling_party')
        profile_key = party if party in policy['default_profiles'] else 'authoritarianism'
        profile = policy['default_profiles'][profile_key]
        subtype = None
        for node in nodes:
            if node.key == 'promote_character' and parent.get(node.val('ideology')) == party:
                subtype = node.val('ideology')
        if subtype is None:
            for node in nodes:
                if node.key == 'recruit_character':
                    for sub in roles.get(node.value, []):
                        if parent.get(sub) == party:
                            subtype = sub
                elif node.key == 'create_country_leader' and parent.get(node.val('ideology')) == party:
                    subtype = node.val('ideology')
        regime = policy['regime_by_subtype'].get(subtype, profile['regime'])
        regime_basis = ('现有党首子类临时推定：' + subtype) if subtype in policy['regime_by_subtype'] else ('临时模板：' + profile_key)
        economic = next((n.key.removeprefix('APDC_set_economic_system_') for n in reversed(nodes) if n.key.startswith('APDC_set_economic_system_')), None)
        economic_basis = '现有国家历史明确设置'
        if economic is None:
            for branch in economic_init.children:
                limit = branch.get('limit')
                if branch.key == 'else' or (limit and condition(limit.children, tag, party, subjects)):
                    economic = next(n.key.removeprefix('APDC_set_economic_system_') for n in branch.children if n.key.startswith('APDC_set_economic_system_'))
                    break
            economic_basis = '只读推算现有经济初始化分类；未执行脚本'
        override = policy['country_overrides'].get(tag, {})
        if 'regime' in override:
            regime = override['regime']
            regime_basis = override['basis']
        if 'economic_system' in override:
            economic = override['economic_system']
            economic_basis = override['basis']
        assert economic in policy['economic_names'], (tag, economic)
        assert regime in policy['regimes'], (tag, regime)
        reforms = {k: profile[k] for k in policy['law_options']}
        reforms.update(override.get('reforms', {}))
        elections = {
            'enabled': politics.get('elections_allowed') != 'no',
            'interval_months': policy['elections']['default_interval_months'],
            'first_date_basis': '开局日期或本国释放日期起算；真实日期由实装时的游戏日历计算',
            'basis': '临时继承历史明确无选举设置；其余采用两年默认周期'
        }
        elections.update(override.get('elections', {}))
        if not elections['enabled']:
            elections['interval_months'] = None
        else:
            assert isinstance(elections['interval_months'], int) and elections['interval_months'] > 0
        coalition = []
        for node in nodes:
            match = re.fullmatch(r'APDC_add_(.+)_to_governing_coalition', node.key)
            if match and match[1] in policy['ideology_order'] and match[1] not in coalition:
                coalition.append(match[1])
        if party and party not in coalition:
            coalition.insert(0, party)
        notes = ['政体和四组改革档位均为临时分配，待剧情修订。']
        if party is None:
            notes.append('未检测到明确执政党；只借用临时模板，不为国家写入意识形态。')
        if any(n.key in ('if', 'else_if', 'else') for n in nodes):
            notes.append('国家历史含条件分支；此初稿未模拟DLC/条件效果，实装时须复核。')
        entries[tag] = {
            'name': country_names.get(tag + '_' + str(party), country_names.get(tag, tag)),
            'has_starting_territory': owner_counts[tag] > 0,
            'starting_state_count': owner_counts[tag],
            'history': path.relative_to(ROOT).as_posix(),
            'observed_ruling_party': party,
            'observed_ruling_subtype': subtype,
            'political_system': regime,
            'political_system_name': policy['regimes'][regime]['name'],
            'political_system_basis': regime_basis,
            'economic_system': economic,
            'economic_system_name': policy['economic_names'][economic],
            'economic_system_basis': economic_basis,
            'reforms': reforms,
            'reforms_basis': '逐国临时覆盖' if override.get('reforms') else '用户授权的临时模板：' + profile_key,
            'elections': elections,
            'opening_governing_coalition': coalition,
            'electoral_alliance_setup': '由剧情明确登记；不从当前执政联盟自动创建新选举同盟',
            'banned_parties': [],
            'seat_coefficients': {p: 0 for p in policy['ideology_order']},
            'extra_government_attitude': {p: 0 for p in policy['ideology_order']},
            'opening_seats': '初始化时从当前民意计算并存档，本初稿不预先抽签或改写支持率',
            'research_scope_hooks': policy['research_hooks'],
            'review_notes': notes
        }
    regimes = collections.Counter(c['political_system'] for c in entries.values())
    for entry in entries.values():
        for group, value in entry['reforms'].items():
            assert value in policy['law_options'][group]
    return {
        'schema_version': 1, 'date': '2026-11-07',
        'status': 'provisional_design_only_not_loaded',
        'scenario_start': '2060.1.1',
        'summary': {
            'registered_countries': len(entries),
            'starting_owners': sum(c['has_starting_territory'] for c in entries.values()),
            'release_only_countries': sum(not c['has_starting_territory'] for c in entries.values()),
            'regime_counts': dict(sorted(regimes.items()))
        },
        'source_sha256': sources,
        'countries': entries
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--policy', type=Path, default=ROOT / 'docs/parliament/20261107-design/opening_policy.json')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--replace-draft', action='store_true')
    args = ap.parse_args()
    output = args.output.resolve()
    allowed_root = (ROOT / 'docs/parliament').resolve()
    if not output.is_relative_to(allowed_root) or output.suffix != '.json':
        ap.error('Output must be a JSON under docs/parliament; runtime destinations are forbidden')
    if output.exists() and not args.replace_draft:
        ap.error('Output exists; edit policy and explicitly use --replace-draft after preserving manual edits')
    policy = json.loads(args.policy.read_text(encoding='utf-8-sig'))
    result = build(policy)
    result['policy'] = args.policy.resolve().relative_to(ROOT).as_posix()
    result['policy_sha256'] = hashlib.sha256(args.policy.read_bytes()).hexdigest()
    result['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
