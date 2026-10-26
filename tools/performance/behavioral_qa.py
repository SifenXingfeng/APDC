"""Install engine assertions into the disposable performance profile only."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'economy'))
import functional_qa
from repair import ROOT,OUT,files,parse,walk,patches,text
from common import lower_math

QA=Path('D:/APDC_PerformanceQA_20261023')
def build():
 functional_qa.QA=QA
 (QA/'driver/common/scripted_effects').mkdir(parents=True,exist_ok=True)
 functional_qa.build()
 p=QA/'driver/common/scripted_effects/APDC_economy_qa.txt';raw=p.read_text('utf-8')
 techs={n.key for rel,p in files('common/technologies').items() for r in parse(p.read_text('utf-8-sig')) if r.key=='technologies' for n in r.children if n.value is None}
 edits=[]
 for n in walk(parse(raw)):
  if n.key=='set_technology':edits.extend((c.start,c.end,'') for c in n.children if c.key not in techs and c.key not in ['popup','show_tech_effect'])
 p.write_text(patches(raw,edits),'utf-8')
 for rel,flags in [
  ('common/on_actions/GFCC_area_se_up.txt',['APDC_region_daily_lock','APDC_region_weekly_lock']),
  ('common/on_actions/zz_APDC_economy.txt',['APDC_eco_daily_tick_lock','APDC_eco_weekly_tick_lock']),
  ('common/on_actions/APDC_economic_system_on_actions.txt',['APDC_system_monthly_lock']),
  ('common/on_actions/APDC_land_units.txt',['APDC_units_monthly_lock'])]:
  raw=text(rel)
  for flag in flags:
   import re
   raw=re.sub(r'(set_global_flag\s*=\s*\{\s*flag\s*=\s*'+flag+r'\s+value\s*=\s*1\s+days\s*=\s*\d+\s*})',r'\1\nadd_to_variable = { global.QA_'+flag+r' = 1 }',raw)
  p=QA/'driver'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(raw,'utf-8')
 # These assertions distinguish country pulse counts from global work counts.
 from functional_qa import assertion
 body=''
 for label,condition in [
  ('region_world_pass_once_daily','check_variable = { global.QA_APDC_region_daily_lock = APDC_eco_day_ticks }'),
  ('economy_world_pass_once_daily','check_variable = { global.QA_APDC_eco_daily_tick_lock = APDC_eco_day_ticks }'),
  ('region_world_pass_once_weekly','check_variable = { global.QA_APDC_region_weekly_lock = APDC_eco_week_ticks }'),
  ('economy_world_pass_once_weekly','check_variable = { global.QA_APDC_eco_weekly_tick_lock = APDC_eco_week_ticks }')]:body+=assertion(label,condition)
 on='on_actions = { on_daily_GER = { effect = {\nif = { limit = { date > 2060.1.16 NOT = { has_country_flag = QA_pulses_tested } } set_country_flag = QA_pulses_tested\n'+body+'}\n'
 on+='if = { limit = { date > 2060.2.2 NOT = { has_country_flag = QA_monthly_tested } } set_country_flag = QA_monthly_tested\n'+assertion('monthly_system_pass_once','check_variable = { global.QA_APDC_system_monthly_lock = 1 }')+assertion('monthly_unit_pass_once','check_variable = { global.QA_APDC_units_monthly_lock = 1 }')+'}\n} } }\n'
 (QA/'driver/common/on_actions/zzzzz_APDC_pulse_assertions.txt').write_text(on,'utf-8')
 print('Added six actual pulse-count assertions; all fixtures stay outside the project')

if __name__=='__main__':build()
