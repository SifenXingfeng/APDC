"""Create an isolated game profile, leaving the user's saves/playset/settings untouched."""
from pathlib import Path
import json,re
from build_core import ROOT,WORK
from cw import render

QA=Path('D:/APDC_UnitQA_20260915')
QA.mkdir(exist_ok=True)
(QA/'mod').mkdir(exist_ok=True)
descriptor=(ROOT/'descriptor.mod').read_text('utf-8-sig')
descriptor=re.sub(r'^path=.*$',f'path="{ROOT.as_posix()}"',descriptor,flags=re.M)
(QA/'mod/APDC.mod').write_text(descriptor,'utf8')
(QA/'dlc_load.json').write_text(json.dumps({'enabled_mods':['mod/APDC.mod','mod/APDC_QA.mod'],'disabled_dlcs':[]}),'utf8')
driver=QA/'qa_mod'
(driver/'common/on_actions').mkdir(parents=True,exist_ok=True)
(driver/'history/units').mkdir(parents=True,exist_ok=True)
(driver/'common/defines').mkdir(parents=True,exist_ok=True)
# Test-only wall-clock acceleration; no combat/economy defines changed.
(driver/'common/defines/zz_APDC_qa_speed.lua').write_text('NDefines.NGame.GAME_SPEED_SECONDS = { 0.01, 0.01, 0.01, 0.01, 0.0 }\n','utf8')
(QA/'mod/APDC_QA.mod').write_text('name="APDC isolated unit validation"\npath="'+driver.as_posix()+'"\ndependencies={ "少女前线-APDC" }\nsupported_version="1.19.*"\n','utf8')
units=json.loads((WORK/'normalized_units.json').read_text('utf8'))
from catalog import EQUIPMENT_NAMES,UNIT_IDS
qa_effects=[('country_event',{'id':'APDC_UNITS.1'}),('set_technology',{'APDC_land_units_easter_eggs':1,'popup':'no'}),('load_oob','APDC_qa_spawn'),('log','"APDC_QA spawned roster fixtures"')]
for eq in EQUIPMENT_NAMES:
    key='apdc_'+eq+'_equipment'
    qa_effects.append(('if',{'limit':{'has_equipment':{key+ ' >':0}},'log':'"APDC_QA EQUIPMENT_OK '+key+'"'}))
qa_effects.append(('if',{'limit':{'num_divisions >':81},'log':'"APDC_QA DIVISIONS_82_OK"'}))
for eq in EQUIPMENT_NAMES:
    qa_effects.append(('add_equipment_production',{
        'equipment':{'type':'apdc_'+eq+'_equipment_1','creator':'GER'},
        'requested_factories':1,'efficiency':.1,'progress':.35}))
qa_effects.append(('log','"APDC_QA PRODUCTION_REQUESTS_31_DONE"'))
# Comparison keys are serialized explicitly for Clausewitz (not key = > value).
effects_text=render(qa_effects,3).replace(' > =',' >')
(driver/'common/on_actions/zz_APDC_runtime_test.txt').write_text('on_actions = { on_startup = { effect = { GER = {\n'+effects_text+'\n} } } }\n','utf8')
templates=[]
for index in (16,17):
    u=units[index-1]
    templates.append(('division_template',{'name':'"列装测试 '+u['name']+'"','regiments':{u['id']:{'x':0,'y':0}}}))
divisions=[('division',{'name':'"QA%02d '%u['index']+u['name']+'"','location':6521,
                       'division_template':'"列装测试 '+u['name']+'"','start_equipment_factor':1,
                       'start_manpower_factor':1,'start_experience_factor':.2}) for u in units]
(driver/'history/units/APDC_qa_spawn.txt').write_text(render(templates)+'units = {\n'+render(divisions,1)+'}\n','utf8')
(QA/'settings.txt').write_text('''language="l_english"
graphics={
 size={ x=1280 y=720 }
 min_gui={ x=1280 y=720 }
 gui_scale=1.0
 fullScreen=no
 borderless=no
 shadows=no
 multi_sampling=0
 maxanisotropy=0
 vsync=no
}
master_volume=0
music_volume=0
sound_fx_volume=0
save_as_binary=no
''','utf8')
(WORK/'runtime_profile.json').write_text(json.dumps({'userdir':str(QA),'only_mod':str(ROOT),'user_playset_modified':False},indent=2),'utf8')
print(QA)
