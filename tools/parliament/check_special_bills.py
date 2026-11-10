"""Read-only checks for native special-bill content; does not generate files."""
import argparse
import json
import re
from pathlib import Path
from common import ROOT, parse


def audit(root=ROOT):
    effects = {}
    errors = []
    for path in sorted((root / 'common/scripted_effects').glob('*.txt')):
        text = path.read_text('utf-8-sig')
        if not any(marker in text for marker in ('apdc_parl_unlock_special_bill', 'apdc_parl_bill_', '_setup', '_on_submit', '_on_pass', '_on_fail')):
            continue
        for node in parse(text):
            effects.setdefault(node.key, []).append((path, node))

    bills = {}
    for name, definitions in effects.items():
        for path, node in definitions:
            if not any(child.key == 'apdc_parl_unlock_special_bill' for child in node.children):
                continue
            values = {}
            for child in node.children:
                if child.key == 'set_temp_variable':
                    values.update({entry.key: entry.value.strip('"') if entry.value is not None else '' for entry in child.children})
            raw_id = values.get('apdc_parl_arg_ID', '')
            if not re.fullmatch(r'[1-9][0-9]*', raw_id or '') or int(raw_id) > 2147483:
                errors.append(f'{path.name}: {name} requires a positive fixed-point-safe integer ID')
                continue
            ident = int(raw_id)
            bridge = effects.get(f'apdc_parl_bill_{ident}_key', [])
            if len(bridge) != 1:
                errors.append(f'{path.name}: ID {ident} requires exactly one stable identity bridge')
                continue
            identity = {}
            for child in bridge[0][1].children:
                if child.key == 'set_temp_variable':
                    identity.update({entry.key: entry.value.strip('"') if entry.value is not None else '' for entry in child.children})
            key = identity.get('apdc_parl_arg_KEY', '')
            if not key.startswith('token:') or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key[6:]):
                errors.append(f'{path.name}: identity bridge requires a literal token:bill_key')
                continue
            key = key[6:]
            if name != key + '_unlock':
                errors.append(f'{path.name}: expected unlock wrapper {key}_unlock')
            if key in bills:
                errors.append(f'duplicate bill key: {key}')
            bills[key] = {'id': ident, 'file': str(path.relative_to(root))}
            for suffix in ('unlock', 'setup', 'on_submit', 'on_pass', 'on_fail'):
                if len(effects.get(key + '_' + suffix, [])) != 1:
                    errors.append(f'{key}: expected exactly one {suffix} effect')

    ids = {}
    for key, bill in bills.items():
        if bill['id'] in ids:
            errors.append(f'duplicate ID {bill["id"]}: {ids[bill["id"]]} and {key}')
        ids[bill['id']] = key
    legacy = root / 'tools/parliament/data/special_bills.json'
    if legacy.is_file():
        for bill in json.loads(legacy.read_text('utf-8'))['bills']:
            if bill['id'] in ids:
                errors.append(f'ID {bill["id"]} also exists in the legacy JSON catalogue')

    tokens = set()
    for path in (root / 'common/synchronized_dynamic_tokens').glob('*.txt'):
        tokens.update(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', re.sub(r'#[^\n]*', '', path.read_text('utf-8-sig'))))
    loc_keys = set()
    for path in (root / 'localisation').rglob('*.yml'):
        loc_keys.update(re.findall(r'^\s*([A-Za-z_][A-Za-z0-9_]*):\d+\s+"', path.read_text('utf-8-sig'), re.M))
    for key in bills:
        for token in (key, key + '_desc'):
            if token not in tokens:
                errors.append(f'{key}: missing synchronized token {token}')
            if token not in loc_keys:
                errors.append(f'{key}: missing localization {token}')
    return {'status': 'passed' if not errors else 'failed', 'bills': bills, 'errors': errors,
            'scope': 'native content structure, stable IDs, callbacks, tokens and localization; no generation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report['errors']))


if __name__ == '__main__':
    main()
