"""Rebuild only parliament UI, assets and its persisted presentation helpers."""
import argparse
import json
import common


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--backup',required=True);args=parser.parse_args()
    common.REPORT=common.ROOT/'docs/parliament/20261107-ui-corrections'
    common.begin(args.backup)
    import assets,backend,cabinet,ui,presentation,specials,laws,verify
    loc={}
    # Build one complete localization catalogue while leaving the existing
    # economic systems, histories and unrelated integration files untouched.
    # The generators' unchanged byte writes are skipped automatically.
    laws.generate(loc);cabinet.generate(loc);backend.generate();assets.generate()
    ui.generate(loc);presentation.generate(loc);specials.generate(loc)
    loc.update({common.P+p+'_seat_factor':common.NAMES[i]+'议员席位系数' for i,p in enumerate(common.PARTIES)})
    loc.update({common.P+'review_speed_factor':'议案审议速度',common.P+'doll_research_factor':'人形科技科研速度',common.P+'relic_project_factor':'遗迹专项计划速度',common.P+'monthly_manpower_factor':'每月人力系数',common.P+'weekly_manpower_factor':'每周人力系数','APDC_eco_private_acquisition_factor':'私营企业收购价格','APDC_eco_private_equipment_purchase_factor':'私营军工装备购买费用',common.P+'party_bonuses':'议会党派影响'})
    common.loc_write(loc)
    tokens=sorted(k for k in loc if k.startswith(common.P))
    tokens+=['APDC_eco_private_acquisition_factor','APDC_eco_private_equipment_purchase_factor']
    common.write('common/synchronized_dynamic_tokens/apdc_parliament_tokens.txt','\n'.join(sorted(set(tokens)))+'\n')
    verify.run()
    print(json.dumps({'status':'generated','report':str(common.REPORT),'backup':args.backup},ensure_ascii=False))


if __name__=='__main__':main()
