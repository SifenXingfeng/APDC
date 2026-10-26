"""Prepare an isolated, hidden HOI4 economy validation profile."""
import json,re,datetime,shutil
from common import *

QA=Path('D:/APDC_EconomyQA_20261023')

def prepare(include_toolpack=False):
 QA.mkdir(exist_ok=True);(QA/'mod').mkdir(exist_ok=True)
 descriptor=(ROOT/'descriptor.mod').read_text('utf-8-sig')
 descriptor=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',descriptor,flags=re.M)
 (QA/'mod/APDC.mod').write_text(descriptor,'utf-8')
 driver=QA/'driver'
 for d in ['common/on_actions','common/defines','common/scripted_effects']: (driver/d).mkdir(parents=True,exist_ok=True)
 (QA/'mod/APDC_EconomyQA.mod').write_text('name="APDC economy validation"\npath="'+driver.as_posix()+'"\ndependencies={ "少女前线-APDC" }\nsupported_version="1.19.*"\n','utf-8')
 enabled=['mod/APDC.mod']
 if include_toolpack:
  toolpack=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/ugc_2913150560.mod')
  shutil.copy2(toolpack,QA/'mod'/toolpack.name);enabled.append('mod/'+toolpack.name)
 enabled.append('mod/APDC_EconomyQA.mod')
 (QA/'dlc_load.json').write_text(json.dumps({'enabled_mods':enabled,'disabled_dlcs':[]}),encoding='utf-8')
 (QA/'settings.txt').write_text('''language="l_simp_chinese"
graphics={ size={ x=1920 y=1080 } min_gui={ x=1280 y=720 } gui_scale=1.0 fullScreen=no borderless=no shadows=no multi_sampling=0 maxanisotropy=0 vsync=no }
master_volume=0
music_volume=0
sound_fx_volume=0
save_as_binary=no
autosave="MONTHLY"
''','utf-8')
 (driver/'common/defines/zzzz_APDC_economy_qa.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.05, 0.05, 0.05, 0.05, 0.0 }\n','utf-8')
 # Diagnostics alter only display selection in the isolated profile.
 on='''on_actions = {
 on_startup = { effect = { GER = {
  set_variable = { APDC_eco_panel_open = 1 }
  set_variable = { APDC_eco_selected_group = 5 }
  APDC_eco_sync_ui = yes
  APDC_eco_calculate_budget = yes
  log = "APDC_ECO_QA START pop=[?APDC_eco_population_m] civ=[?APDC_eco_public_civ] private=[?APDC_eco_private_civ] supply=[?APDC_eco_supply_m] demand=[?APDC_eco_demand_m] cash=[?APDC_eco_cash_m]"
 } } }
 on_daily_GER = { effect = {
  log = "APDC_ECO_QA DAY date=[GetDateText] ticks=[?APDC_eco_day_ticks] weeks=[?APDC_eco_week_ticks] supply=[?APDC_eco_supply_m] demand=[?APDC_eco_demand_m] cash=[?APDC_eco_cash_m] lower=[?APDC_eco_cash_k] balance=[?APDC_eco_weekly_balance_m] velocity=[?APDC_eco_civ_velocity] research=[?APDC_eco_research_active]"
 } }
}
'''
 (driver/'common/on_actions/zzzz_APDC_economy_qa.txt').write_text(on,'utf-8')
 meta={'profile':str(QA),'project':str(ROOT),'user_settings_modified':False,'prepared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (WORK/'runtime_profile.json').write_text(json.dumps(meta,indent=2),'utf-8')
 print(QA)

if __name__=='__main__':
 import sys
 prepare('--include-user-toolpack' in sys.argv)
