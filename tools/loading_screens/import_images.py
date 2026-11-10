"""Import numbered loading art without resampling full-size images.

Stages and verifies every asset before replacing the scoped runtime files.
The menu image is intentionally absent from the explicit background database:
the engine adds the default menu texture itself.
"""
from pathlib import Path
import argparse
import csv
import datetime
import hashlib
import io
import json
import re
import shutil
import struct
import sys
import zipfile

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
GAME = Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
USER = Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
REPORT = ROOT / 'docs/ui/20261109-loading-images'
MENU = 'apdc_mainmenu_14'
ORIGINALS = [f'load_{n}' for n in range(1, 10)] + [
    'load_tfv', 'load_dod', 'load_tiger', 'load_mtg', 'load_mtg_2',
    'load_lar', 'load_botb', 'load_nsb', 'load_nsb2', 'load_bba',
    'load_aat', 'load_aat2', 'load_toa', 'load_ww', 'load_goe',
    'load_ncns_chi', 'load_ncns_jap', 'load_taog_ast',
]
CONFIGS = ['common/frontend/backgrounds/base_backgrounds.txt',
           'interface/frontendmainviewbg.gfx',
           'interface/frontendmainviewbg_basic.gfx',
           'interface/APDC_loading_previews.gfx']
PROTECTED = ['interface/frontendmainview.gui', 'gfx/interface/logo_game.dds',
             'interface/load_screen.gui', 'interface/load_screen.gfx',
             'descriptor.mod', 'gfx/FX/gf_map_style.fxh']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def dds_bytes(image):
    image = image.convert('RGBA')
    w, h = image.size
    header = struct.pack('<7I11I8I5I', 124, 0x100F, h, w, w * 4, 0, 0,
                         *([0] * 11), 32, 0x41, 0, 32, 0xff0000,
                         0xff00, 0xff, 0xff000000, 0x1000, 0, 0, 0, 0)
    return b'DDS ' + header + image.tobytes('raw', 'BGRA')


def original_assets_and_sprites():
    assets, sprites = set(), set()
    bases = [GAME] + sorted(p for p in (GAME / 'dlc').iterdir() if p.is_dir())
    for base in bases:
        for p in (base / 'gfx/loadingscreens').glob('*.dds'):
            if '_small' not in p.stem:
                assets.add(p.stem)
        for p in (base / 'interface').rglob('*.gfx'):
            sprites.update(re.findall(r'\bname\s*=\s*"(GFX_[^"\r\n]+)"',
                                      p.read_text('utf-8-sig', errors='replace')))
        if base == GAME:
            continue
        for zp in base.glob('*.zip'):
            with zipfile.ZipFile(zp) as z:
                for item in z.infolist():
                    rel = item.filename.replace('\\', '/').lstrip('/')
                    if rel.startswith('gfx/loadingscreens/') and rel.endswith('.dds'):
                        stem = Path(rel).stem
                        if '_small' not in stem:
                            assets.add(stem)
                    elif rel.startswith('interface/') and rel.endswith('.gfx'):
                        sprites.update(re.findall(r'\bname\s*=\s*"(GFX_[^"\r\n]+)"',
                                                  z.read(item).decode('utf-8-sig', errors='replace')))
    return assets, sprites


def sprite(name, texture, size, small=False):
    w, h = size
    return (f'\tcorneredTileSpriteType = {{\n\t\tname = "{name}"\n'
            f'\t\ttexturefile = "{texture}"\n\t\tborderSize = {{ x=0 y=0 }}\n'
            f'\t\tsize = {{ x={w} y={h} }}\n\t\ttilingCenter = no\n'
            '\t\teffectFile = "gfx/FX/buttonstate.shader"\n\t}\n')


def run(source, apply):
    files = sorted(source.glob('*.png'), key=lambda p: int(p.stem))
    assert [int(p.stem) for p in files] == list(range(1, 63)), 'Expected 1.png through 62.png'
    originals, native_sprites = original_assets_and_sprites()
    assert originals == set(ORIGINALS), ('Installed original background inventory changed', originals ^ set(ORIGINALS))
    sys.path.insert(0, str(ROOT / 'tools/unit_overhaul'))
    from cw import parse
    registry = parse((GAME / CONFIGS[0]).read_text('utf-8-sig'))
    assert {n.key for n in registry} == originals
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    backup = ROOT.parent / '.codex_backups/APDC' / (now.strftime('%Y%m%d-%H%M%S') + '-loading-images-62')
    backup.mkdir(parents=True, exist_ok=False)
    stage = backup / 'stage'
    old = sorted((ROOT / 'gfx/loadingscreens').glob('*.dds'))
    before = {}
    context = [ROOT / rel for rel in CONFIGS + PROTECTED]
    context += [ROOT / '项目接手文档/00_快速接手/当前状态与未完成事项.md']
    for p in old + context:
        rel = p.relative_to(ROOT).as_posix()
        before[rel] = {'existed': p.exists(), 'sha256': sha(p) if p.exists() else None}
        if p.exists():
            target = backup / 'before' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    for p in files:
        target = backup / 'inputs' / p.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    for p in (USER / 'logs').glob('*.log'):
        target = backup / 'logs' / p.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    for p in [USER / 'settings.txt', USER / 'pdx_settings.txt', USER / 'dlc_load.json', USER / 'mod/APDC.mod']:
        if p.exists():
            target = backup / 'user-context' / p.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    dump(backup / 'before-manifest.json', {'timestamp': now.isoformat(), 'files': before})
    print('Backup: ' + str(backup), flush=True)
    original_iter = iter(ORIGINALS)
    records, catalog, previews = [], [], []
    for p in files:
        index = int(p.stem)
        if index == 14:
            stem, role = MENU, 'main_menu_engine_added'
        elif index <= 28:
            stem, role = next(original_iter), 'original_override'
        else:
            stem, role = f'load_apdc_{index:03d}', 'new_loading_path'
        rel = f'gfx/loadingscreens/{stem}.dds'
        small_rel = f'gfx/loadingscreens/{stem}_small.dds'
        with Image.open(p) as original:
            image = original.convert('RGBA')
        encoded = dds_bytes(image)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded)
        with Image.open(target) as check:
            assert check.size == image.size and check.convert('RGBA').tobytes() == image.tobytes(), p
        thumb = Image.new('RGBA', (192, 144), (0, 0, 0, 0))
        fit = ImageOps.contain(image, (192, 144), Image.Resampling.LANCZOS)
        thumb.paste(fit, ((192 - fit.width) // 2, (144 - fit.height) // 2))
        (stage / small_rel).write_bytes(dds_bytes(thumb))
        with Image.open(stage / small_rel) as check:
            assert check.convert('RGBA').tobytes() == thumb.tobytes()
        small_name = f'GFX_{stem}_small'
        if small_name not in native_sprites:
            previews.append(sprite(small_name, small_rel, (192, 144), True))
        if index != 14:
            field = ''
            if image.size != (1920, 1440):
                special = f'GFX_APDC_loading_image_{index}'
                previews.append(sprite(special, rel, image.size))
                field = f' gfx = {special} '
            catalog.append(f'{stem} = {{{field}}}\n')
        records.append({'index': index, 'source_file': p.name, 'source_sha256': sha(p),
                        'size': list(image.size), 'role': role, 'stem': stem,
                        'path': rel, 'thumbnail': small_rel, 'dds_sha256': sha(target),
                        'thumbnail_sha256': sha(stage / small_rel),
                        'rgba_sha256': hashlib.sha256(image.tobytes()).hexdigest(),
                        'fullsize_pixel_identical': True, 'fullsize_resized': False,
                        'explicit_frontend_registration': index != 14})
        if index % 10 == 0 or index == 62:
            print(f'Staged and pixel-verified {index}/62', flush=True)
    assert next(original_iter, None) is None
    assert len(catalog) == 61 and len({r['path'] for r in records}) == 62
    menu_record = records[13]
    graphics = 'spriteTypes = {\n' + sprite('GFX_frontend_bg', menu_record['path'], (1920, 1440))
    graphics += sprite('GFX_frontend_bg_simp_chinese', menu_record['path'], (1920, 1440)) + '}\n'
    basic = 'spriteTypes = {\n' + sprite('GFX_frontend_bg_basic', menu_record['path'], (1920, 1440))
    basic += sprite('GFX_frontend_bg_basic_small', menu_record['thumbnail'], (192, 144)) + '}\n'
    configs = {CONFIGS[0]: '# APDC numbered art. Main menu 14 is added by the engine, not registered twice.\n' + ''.join(catalog),
               CONFIGS[1]: graphics, CONFIGS[2]: basic,
               CONFIGS[3]: 'spriteTypes = {\n' + ''.join(previews) + '}\n'}
    for rel, text in configs.items():
        parse(text)
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, 'utf-8')
    manifest = {'timestamp': now.isoformat(), 'source_directory': str(source),
                'backup': str(backup), 'images': records, 'original_override_count': 27,
                'new_loading_count': 34, 'exclusive_menu_image': 14,
                'explicit_backgrounds': 61, 'expected_engine_backgrounds': 62,
                'dds_encoding': 'uncompressed BGRA32; full-size pixels unchanged',
                'thumbnail_policy': '192x144, preserve aspect, transparent padding if needed',
                'old_runtime_files': [p.relative_to(ROOT).as_posix() for p in old]}
    dump(backup / 'import-manifest.json', manifest)
    if not apply:
        print('Stage only; pass --apply to replace the runtime files.', flush=True)
        return
    for rel, item in before.items():
        p = ROOT / rel
        assert p.exists() == item['existed'] and (not p.exists() or sha(p) == item['sha256']), ('Concurrent change', rel)
    staged = sorted(p for p in stage.rglob('*') if p.is_file())
    final_paths = {p.relative_to(stage).as_posix() for p in staged}
    for p in staged:
        target = ROOT / p.relative_to(stage)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    removed = []
    directory = (ROOT / 'gfx/loadingscreens').resolve()
    for p in old:
        rel = p.relative_to(ROOT).as_posix()
        if rel not in final_paths:
            assert p.resolve().parent == directory and p.suffix.lower() == '.dds'
            p.unlink()
            removed.append(rel)
    for rel in PROTECTED:
        assert sha(ROOT / rel) == before[rel]['sha256'], rel
    for p in staged:
        assert sha(ROOT / p.relative_to(stage)) == sha(p)
    expected = {r['path'] for r in records} | {r['thumbnail'] for r in records}
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'gfx/loadingscreens').glob('*.dds')}
    assert expected == actual and len(actual) == 124
    manifest['removed_obsolete_paths'] = removed
    manifest['applied'] = True
    dump(REPORT / 'manifest.json', manifest)
    dump(backup / 'import-manifest.json', manifest)
    with (REPORT / 'mapping.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['source_number', 'source_file', 'role', 'runtime_path', 'size', 'explicit_frontend_registration'])
        for r in records:
            w.writerow([r['index'], r['source_file'], r['role'], r['path'], 'x'.join(map(str, r['size'])), r['explicit_frontend_registration']])
    print(json.dumps({'applied': True, 'backup': str(backup), 'original_overrides': 27,
                      'new_loading_paths': 34, 'exclusive_menu': 14, 'big_images': 62,
                      'thumbnails': 62, 'explicit_registry': 61, 'removed': removed}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('D:/Desktop/加载图定图'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(args.source, args.apply)
