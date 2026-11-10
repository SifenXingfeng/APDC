"""Build parliament from editable local source data; never run the game."""
import argparse
import subprocess
from common import *


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--backup',type=Path)
    ap.add_argument('--import-data',action='store_true')
    ap.add_argument('--assets-only',action='store_true')
    ap.add_argument('--game-dir',type=Path,help='HOI4 installation directory used for native artwork')
    args=ap.parse_args()
    if args.game_dir:
        import common
        common.GAME=args.game_dir.resolve()
    backup=begin(args.backup)
    if not (backup/'git-status-before.txt').exists():
        (backup/'git-status-before.txt').write_bytes(subprocess.run(['git','status','--porcelain=v1','--untracked-files=no'],cwd=ROOT,capture_output=True,check=True).stdout)
    from import_data import import_sources
    from cabinet import import_candidates
    if args.import_data or not (DATA/'laws.json').exists():import_sources()
    if not (DATA/'candidates.json').exists():import_candidates()
    import assets
    assets.generate()
    if args.assets_only:
        print(json.dumps({'backup':str(backup),'phase':'assets_and_catalogues','candidates':len(load_json('candidates.json')['candidates'])},ensure_ascii=False));return
    settings=load_json('settings.json')
    assert settings['manpower_mode']['monthly'] in ('population','pool')
    assert settings['manpower_mode']['weekly'] in ('population','pool')
    import backend,laws,economy,cabinet,ui,presentation,integration,specials
    loc={}
    laws.generate(loc)
    economy.generate(loc)
    cabinet.generate(loc)
    backend.generate()
    ui.generate(loc)
    presentation.generate(loc)
    specials.generate(loc)
    integration.generate()
    loc.update({P+p+'_seat_factor':NAMES[i]+'议员席位系数' for i,p in enumerate(PARTIES)})
    loc[P+'review_speed_factor']='议案审议速度'
    loc[P+'doll_research_factor']='人形科技科研速度'
    loc[P+'relic_project_factor']='遗迹专项计划速度'
    loc[P+'monthly_manpower_factor']='每月人力系数'
    loc[P+'weekly_manpower_factor']='每周人力系数'
    loc['APDC_eco_private_acquisition_factor']='私营企业收购价格'
    loc['APDC_eco_private_equipment_purchase_factor']='私营军工装备购买费用'
    loc[P+'party_bonuses']='议会党派影响'
    loc_write(loc)
    tokens=sorted({k for k in loc if k.startswith(P)}|{P+p+'_seat_factor' for p in PARTIES}|{P+'review_speed_factor',P+'doll_research_factor',P+'relic_project_factor',P+'monthly_manpower_factor',P+'weekly_manpower_factor','APDC_eco_private_acquisition_factor','APDC_eco_private_equipment_purchase_factor'})
    write('common/synchronized_dynamic_tokens/apdc_parliament_tokens.txt','\n'.join(tokens)+'\n')
    # Ordinary starting election fields use the native calendar. Keep the
    # existing ruling party, popularity, identities, OOB and all other history.
    opening=load_json('opening_countries.json')
    for path in sorted((ROOT/'history/countries').glob('*.txt')):
        tag=path.name[:3]
        if tag not in opening:continue
        c=opening[tag];body=path.read_bytes().decode('utf-8-sig')
        start='# APDC parliament election calendar schema 1'
        if start in body:body=body[:body.index(start)].rstrip()+'\n'
        original_path=backup/'files'/path.relative_to(ROOT)
        if original_path.exists():
            original=original_path.read_bytes().decode('utf-8-sig')
            if original.replace('\r\n','\n').rstrip()==body.replace('\r\n','\n').rstrip():body=original.rstrip()
        newline='\r\n' if '\r\n' in body else '\n'
        allowed='yes' if c['elections']['enabled'] else 'no'
        month=c['elections']['interval_months'] or 24
        # Runtime history effects also require an explicit ruling party. Test
        # the already-resolved party, preserving dated/conditional history.
        calendar=''.join(iff('has_government = '+party,'set_politics = { ruling_party = '+party+' last_election = "2060.1.1" election_frequency = '+str(month)+' elections_allowed = '+allowed+' }\n') for party in PARTIES)
        body+=newline+newline+start+newline+calendar.replace('\n',newline)
        write(path.relative_to(ROOT).as_posix(),body)
    json_write('docs/parliament/20261107-implementation/build.json',{'status':'generated_not_yet_runtime_verified','backup':str(backup),'law_groups':6,'law_options':43,'seats':500,'candidates':len(load_json('candidates.json')['candidates']),'source_settings':settings})
    print(json.dumps({'backup':str(backup),'phase':'runtime_generated','localisation_keys':len(loc),'candidates':len(load_json('candidates.json')['candidates'])},ensure_ascii=False))


if __name__=='__main__':main()
