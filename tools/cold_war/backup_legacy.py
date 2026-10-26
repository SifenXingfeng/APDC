"""Back up exact legacy subsystem bytes before removing only its exclusive files."""
import datetime, hashlib, json, shutil, re
from common import ROOT, OUT, ART

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT/'backup.json'
    if manifest.exists():
        return json.loads(manifest.read_text('utf-8'))
    legacy = []
    markers = re.compile(r'APDC_game_|APDC_SOV_tendency|APDC_USA_tendency|FRA_game_|ENG_game_|LUX_game_|APDC_play_a_game|General_play_a_game|apdc_game_war')
    for folder in ('common','events','interface','localisation'):
        for p in (ROOT/folder).rglob('*'):
            if p.suffix not in ('.txt','.gui','.gfx','.yml'): continue
            if markers.search(p.read_text('utf-8-sig')):
                # Never remove a mixed-purpose file based on a string match.
                if 'play_a_game' not in p.name and p.name not in ('APDC_game_country_introduce.txt','APDC_game_war_status.txt','APDC_dynamic_modifiers.txt'):
                    raise RuntimeError('Audit mixed-purpose legacy reference: '+str(p))
                legacy.append(p)
    assets = list((ROOT/'gfx/interface/play_a_game_gui').glob('*'))
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = ROOT.parent/'.codex_backups/APDC'/f'{stamp}-cold-war'
    backup.mkdir(parents=True)
    hashes = {}
    for p in legacy+assets:
        if not p.is_file(): continue
        rel=p.relative_to(ROOT).as_posix(); dest=backup/'original'/rel
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
        hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    shutil.copytree(ART,backup/'input-art')
    protected={}
    for folder in ('common','events','history','interface','localisation','map'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p not in legacy and p not in assets:
                protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    (backup/'protected-sha256.json').write_text(json.dumps(protected,indent=2),'utf-8')
    result={'backup':str(backup),'legacy_files':[p.relative_to(ROOT).as_posix() for p in legacy],
            'legacy_assets':[p.relative_to(ROOT).as_posix() for p in assets if p.is_file()], 'sha256':hashes}
    manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    (backup/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    # Preserve the old entry button art under the new subsystem before removal.
    newart=ROOT/'gfx/interface/APDC/cold_war';newart.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'gfx/interface/play_a_game_gui/APDC_game_start_button_icon.dds',newart/'entry.dds')
    for p in legacy+assets:
        assert p.resolve().is_relative_to(ROOT.resolve())
        assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p.relative_to(ROOT).as_posix()]
        p.unlink()
    return result

if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2))
