"""Generate the deterministic economy backend; UI actions call this same API."""
import json,re
from common import *
from build_data import TRACKS, LAWS, build as build_data

P='APDC_eco_'
def effect(name,s): return block(P+name,s)
def var(name): return P+name
def mod(name): return 'modifier@'+P+name
def lim(n,minimum=0,maximum=None):
 return 'clamp_variable = { var = '+var(n)+f' min = {minimum}'+(f' max = {maximum}' if maximum is not None else '')+' }\n'
def add(n,v): return f'add_to_variable = {{ {var(n)} = {v} }}\n'
def mcalc(n,base,m): return calc(n,base,('multiply','{ value = '+mod(m)+' add = 1 max = 0 }'))

def build_migration():
 """Only replace modifier keys, leaving country-specific scripts and values intact."""
 # Preserve native fall-through definitions and change only their consumer
 # modifier keys. A folder replacement would import unrelated gameplay.
 replaces=re.findall(r'replace_path\s*=\s*"([^"]+)"',(ROOT/'descriptor.mod').read_text('utf-8-sig'))
 native_manifest=WORK/'native_modifier_overrides.json'
 native_overrides=json.loads(native_manifest.read_text('utf-8')) if native_manifest.exists() else []
 for native in (GAME/'common').rglob('*.txt'):
  rel=native.relative_to(GAME);target=ROOT/rel
  if target.exists() or any(rel.as_posix().startswith(x+'/') for x in replaces):continue
  source=native.read_text('utf-8-sig')
  if not re.search(r'\bconsumer_goods_(factor|expected_value)\s*=',source):continue
  write(rel,source);native_overrides.append(rel.as_posix())
 native_manifest.write_text(json.dumps(sorted(set(native_overrides)),indent=2),'utf-8')
 focus_ids=set()
 for p in (ROOT/'common/national_focus').rglob('*.txt'):
  focus_ids.update(re.findall(r'\bid\s*=\s*([A-Za-z0-9_]+)',p.read_text('utf-8-sig')))
 decision_ids=set()
 for p in (ROOT/'common/decisions').glob('*.txt'):
  decision_ids.update(re.findall(r'\b([A-Za-z0-9_]+)\s*=\s*\{',p.read_text('utf-8-sig')))
 effect_ids=set()
 for p in effective_files('common/scripted_effects'):
  effect_ids.update(re.findall(r'^\s*([A-Za-z0-9_]+)\s*=\s*\{',p.read_text('utf-8-sig'),re.M))
 compatibility_file=WORK/'native_law_compatibility.json'
 compatibility=json.loads(compatibility_file.read_text('utf-8')) if compatibility_file.exists() else []
 changed=[]
 for folder in ['common','events']:
  for p in (ROOT/folder).rglob('*.txt'):
   if p.name.startswith('APDC_economy_'): continue
   s=p.read_text('utf-8-sig'); t=re.sub(r'\bconsumer_goods_factor(?=\s*=)',P+'population_factor',s)
   if p.name=='_economic.txt':
    nodes=parse(t); econ=nodes[0].get('economy'); edits=[]
    values={'undisturbed_isolation':1,'isolation':1,'civilian_economy':1,
      'low_economic_mobilisation':.85,'partial_economic_mobilisation':.7,'war_economy':.55,'tot_economic_mobilisation':.4}
    for idea in econ.children:
     m=idea.get('modifier')
     if m and idea.key in values:
      x=m.get('consumer_goods_expected_value')
      if x: edits.append((x.start,x.end,P+'population_base = '+str(values[idea.key])))
    t=patches(t,edits)
   t=re.sub(r'\bconsumer_goods_expected_value(?=\s*=)',P+'population_factor',t)
   if p.name in ['_trade.txt','_economic.txt']:
    nodes=parse(t);edits=[]
    for category in nodes[0].children:
     for idea in category.children:
      if idea.key not in ['free_trade','export_focus','limited_exports','closed_economy']:continue
      m=idea.get('modifier')
      if m and not m.get(P+'consumer_trade_freedom'):
       freedom={'free_trade':.8,'export_focus':.5,'limited_exports':.25,'closed_economy':0}[idea.key]
       tariff={'free_trade':0,'export_focus':1,'limited_exports':2.5,'closed_economy':0}[idea.key]
       edits.append((m.value_end-1,m.value_end-1,f'\n{P}consumer_trade_freedom = {freedom}\n{P}consumer_tariff = {tariff}\n'))
    t=patches(t,edits)
   if p.name=='_economic.txt':
    edits=[]
    for n in walk(parse(t)):
     if n.key=='has_completed_focus' and n.value and n.value.strip('"') not in focus_ids:
      edits.append((n.start,n.end,'always = no'))
      compatibility.append({'kind':'absent_focus_condition','original':t[n.start:n.end],'replacement':'always = no'})
     if n.key=='has_active_mission' and n.value and n.value.strip('"') not in decision_ids:
      edits.append((n.start,n.end,'always = no'))
      compatibility.append({'kind':'absent_mission_condition','original':t[n.start:n.end],'replacement':'always = no'})
     if n.key in ['SIA_increase_civilian_approval','SIA_decrease_civilian_approval','SIA_increase_military_approval','SIA_decrease_military_approval'] and n.key not in effect_ids:
      edits.append((n.start,n.end,'hidden_effect = { }'))
      compatibility.append({'kind':'absent_legacy_approval_hook','original':t[n.start:n.end],'replacement':'hidden_effect = { }'})
    t=patches(t,edits)
   if t!=s:
    # Preserve BOM of any exceptional existing file; new scripts have no BOM.
    p.write_text(t,encoding='utf-8-sig' if p.read_bytes().startswith(b'\xef\xbb\xbf') else 'utf-8',newline='\n'); changed.append(str(p.relative_to(ROOT)))
 # Native laws already migrate base demand; all native automatic reservation is disabled.
 write('common/defines/zzzz_APDC_economy.lua',
  'NDefines.NProduction.MINIMUM_NUMBER_OF_FACTORIES_TAKEN_BY_CONSUMER_GOODS_VALUE = 0\n'
  'NDefines.NProduction.MINIMUM_NUMBER_OF_FACTORIES_TAKEN_BY_CONSUMER_GOODS_PERCENT = 0\n')
 write('common/buildings/APDC_economy_buildings.txt',block('buildings',
  ''.join(block(P+'private_'+k,f'base_cost = {cost}\nicon_frame = {icon}\nvalue = {val}\nhide_if_missing_tech = yes\nlevel_cap = {{ shares_slots = yes state_max = 50 }}')
  for k,cost,icon,val in [('civ',10800,1,5),('mil',7200,2,8)])))
 write('common/dynamic_modifiers/APDC_economy_dynamic_modifiers.txt',block(P+'allocation',
  'enable = { has_country_flag = APDC_eco_initialized }\n'
  'civilian_factory_use = APDC_eco_public_civ\nconsumer_goods_expected_value = -1\n'))
 (WORK/'modifier_migration.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding='utf-8')
 compatibility_file.write_text(json.dumps(compatibility,ensure_ascii=False,indent=2),'utf-8')

def build_laws(data):
 s=''
 s+=effect('is_planned_placeholder','') if False else ''
 triggers=block(P+'is_planned','OR = { has_idea = APDC_economic_system_decentralized_planning_idea has_idea = APDC_economic_system_central_planning_idea }')
 s+=effect('change_law',cond('has_country_flag = APDC_eco_initialized '+check('selected_group','>','0')+' has_political_power > 149 '+check('cash_m','>=',0),
  ''.join(cond(check('selected_group','=',i),
   ''.join(cond(check('requested_law','=',j)+' NOT = { has_idea = '+P+key+'_'+str(j)+' } '+
     ((P+'is_planned = yes') if key=='distribution' and j==5 else (P+'is_planned = no') if key=='distribution' else ''),
    'add_political_power = -150\n'+''.join('remove_ideas = '+P+key+'_'+str(k)+'\n' for k in range(1,6))+
    'add_ideas = '+P+key+'_'+str(j)+'\nAPDC_eco_refresh_policies = yes\nAPDC_eco_refresh_current_supply = yes\nAPDC_eco_calculate_budget = yes\n') for j in range(1,6)))
   for i,(key,*_) in enumerate(LAWS,1))))
 # Derived values read the *aggregate* modifier, so ideas, focuses and events stack.
 # Formulas already read the aggregate modifier directly. Do not also copy
 # forty unused modifier values to persistent country variables every day.
 body=setv('population_base','modifier@APDC_eco_population_base')
 body+=cond(check('population_base','<=',0),setv('population_base',1))
 body+=setv('trade_freedom',mod('consumer_trade_freedom'))+lim('trade_freedom',0,1)+setv('tariff',mod('consumer_tariff'))+lim('tariff',0)
 body+=setv('research_slot_target','modifier@APDC_eco_research_slots')
 body+=calc('research_slot_change',var('research_slot_target'),('subtract',var('research_slot_applied')))
 body+=cond(check('research_slot_change','!=',0),'add_research_slot = '+var('research_slot_change')+'\n'+setv('research_slot_applied',var('research_slot_target')))
 s+=effect('refresh_policies',body)
 s+=effect('bankruptcy',cond(check('cash_m','<',0),
  ''.join(cond('OR = { '+ ' '.join('has_idea = '+P+key+'_'+str(j) for j in range(first,6))+' }',
   ''.join('remove_ideas = '+P+key+'_'+str(j)+'\n' for j in range(1,6))+'add_ideas = '+P+key+'_1\n')
   for key,first in [('food_spending',2),('education_spending',2),('medical_spending',2),('development',2),('research',2),('military',2),('investment',2)])+
  cond('OR = { has_idea = APDC_eco_distribution_2 has_idea = APDC_eco_distribution_3 has_idea = APDC_eco_distribution_4 }',
   'remove_ideas = APDC_eco_distribution_2\nremove_ideas = APDC_eco_distribution_3\nremove_ideas = APDC_eco_distribution_4\nadd_ideas = APDC_eco_distribution_1\n')+
  cond('OR = { has_idea = APDC_eco_consumption_4 has_idea = APDC_eco_consumption_5 }',
   'remove_ideas = APDC_eco_consumption_4\nremove_ideas = APDC_eco_consumption_5\nadd_ideas = APDC_eco_consumption_3\n')+
  'APDC_eco_refresh_policies = yes\n'))
 # Each automatic track replaces the former political-law slot; lower welfare
 # tiers have the same authoritative native/custom modifier path as all other laws.
 trackbody=''
 for key,*_ in TRACKS:
  trackbody+=lim(key,1,5)
  for j in range(1,6):
   trackbody+=cond(check(key,'>=',j)+((' '+check(key,'<',j+1)) if j<5 else '')+' NOT = { has_idea = '+P+key+'_'+str(j)+' }',
    ''.join('remove_ideas = '+P+key+'_'+str(k)+'\n' for k in range(1,6))+'add_ideas = '+P+key+'_'+str(j)+'\n')
 s+=effect('sync_development',trackbody)
 write('common/scripted_triggers/APDC_economy_triggers.txt',triggers)
 return s

def build_initialize():
 old=[]
 for fn in ['APDC_scientific_development_laws.txt','APDC_society_development_laws.txt','APDC_poverty_laws.txt']:
  p=ROOT/'common/ideas'/fn; t=p.read_text('utf-8-sig')
  for category in parse(t)[0].children:
   for idea in category.children:
    if idea.value is None: old.append(idea.key)
 b=cond('NOT = { APDC_has_economic_system = yes }','APDC_assign_initial_economic_system = yes\n')+''.join('remove_ideas = '+x+'\n' for x in old)
 b+=setv('society',3)+setv('science',3)+setv('defense',3)+setv('food',3)+setv('education',3)+setv('medical',3)
 b+=cond('OR = { tag = GER tag = SOV tag = USA tag = JAP tag = ENG tag = FRA tag = LLU tag = CAN tag = AST tag = KOR tag = SWE tag = NOR tag = FIN tag = SWI }',
  ''.join(setv(k,4) for k in ['society','science','defense','food','education','medical']))
 b+=cond('OR = { tag = AFG tag = SOM tag = CHA tag = NGR tag = CAR tag = SSD tag = MRT }',
  ''.join(setv(k,2) for k in ['society','science','defense','food','education','medical']))
 b+= ''.join('add_ideas = '+P+k+'_'+str(3 if k in ['tax','food_spending','education_spending','medical_spending','development','research','military','consumption'] else 1)+'\n' for k,*_ in LAWS)
 b+=setv('cash_m',0)+setv('cash_k',0)+setv('public_civ',0)+setv('research_slot_applied',0)+setv('last_civ_capacity',0)
 for k in ['extra_input','extra_output','civ_progress','mil_progress','day_ticks','week_ticks']: b+=setv(k,0)
 b+='set_country_flag = APDC_eco_initialized\nadd_dynamic_modifier = { modifier = APDC_eco_allocation }\n'
 b+='APDC_eco_sync_development = yes\nAPDC_eco_refresh_policies = yes\n'
 # Test opening stock is explicit and recorded. Existing state factories stay intact.
 b+='every_controlled_state = {\n'+cond('is_owned_by = PREV',
  'set_temp_variable = { APDC_eco_seed_civ = non_damaged_building_level@industrial_complex }\n'
  'set_temp_variable = { APDC_eco_seed_mil = non_damaged_building_level@arms_factory }\n'
  'divide_temp_variable = { APDC_eco_seed_civ = 3 }\ndivide_temp_variable = { APDC_eco_seed_mil = 3 }\n'
  'round_temp_variable = APDC_eco_seed_civ\nround_temp_variable = APDC_eco_seed_mil\n'
  'if = { limit = { check_variable = { APDC_eco_seed_civ > 0 } free_building_slots = { building = APDC_eco_private_civ size > 0 } } add_building_construction = { type = APDC_eco_private_civ level = 1 instant_build = yes } }\n'
  'if = { limit = { check_variable = { APDC_eco_seed_mil > 0 } free_building_slots = { building = APDC_eco_private_mil size > 0 } } add_building_construction = { type = APDC_eco_private_mil level = 1 instant_build = yes } }')+'}\n'
 b+='APDC_eco_calculate_country = yes\n'+cond(check('goods_per_civ_m','>',0),calc('public_civ',var('demand_m'),('divide',var('goods_per_civ_m')),('subtract',var('private_civ')),('max',0),('min',var('public_available')),('round','down')))
 b+='APDC_eco_calculate_country = yes\nAPDC_eco_calculate_budget = yes\n'
 b+=calc('cash_m',var('population_m'),('multiply',20),('add',100),('round','down'))
 b+='APDC_eco_assign_validation_cohort = yes\nAPDC_eco_refresh_equipment = yes\nAPDC_eco_reconcile_planned = yes\n'
 return effect('initialize_country',cond('NOT = { has_country_flag = APDC_eco_initialized }',b))

def adapt_system_api():
 p=ROOT/'common/scripted_effects/APDC_economic_system_scripted_effects.txt'
 text=p.read_text('utf-8-sig');edits=[]
 for n in parse(text):
  if not n.key.startswith('APDC_set_economic_system_'):continue
  if 'APDC_eco_reconcile_planned' in text[n.start:n.end]:continue
  edits.append((n.value_end-1,n.value_end-1,'\nif = { limit = { has_country_flag = APDC_eco_initialized } APDC_eco_reconcile_planned = yes APDC_eco_refresh_policies = yes APDC_eco_refresh_current_supply = yes APDC_eco_calculate_budget = yes }\n'))
 if edits:write(p.relative_to(ROOT),patches(text,edits))

def build_country():
 b=setv('population_m',0)+setv('private_civ',0)+setv('private_mil',0)+setv('private_civ_raw',0)+setv('private_mil_raw',0)
 b+='every_controlled_state = {\nset_temp_variable = { APDC_eco_state_pop = state_population_k }\ndivide_temp_variable = { APDC_eco_state_pop = 1000 }\n'
 b+='add_to_variable = { PREV.APDC_eco_population_m = APDC_eco_state_pop }\n'
 b+='set_temp_variable = { APDC_eco_local_multiplier = { value = modifier@local_factories add = 1 max = 0 } }\n'
 for k in ['civ','mil']:
  b+=f'add_to_variable = {{ PREV.APDC_eco_private_{k}_raw = building_level@APDC_eco_private_{k} }}\n'
  b+=f'set_temp_variable = {{ APDC_eco_state_private = {{ value = non_damaged_building_level@APDC_eco_private_{k} multiply = APDC_eco_local_multiplier }} }}\n'
  b+=f'add_to_variable = {{ PREV.APDC_eco_private_{k} = APDC_eco_state_private }}\n'
 b+='}\nset_country_flag = { flag = APDC_eco_statistics_today value = 1 days = 1 }\n'
 statistics=effect('collect_country_statistics',b)
 statistics+=effect('ensure_country_statistics',cond('NOT = { has_country_flag = APDC_eco_statistics_today }','APDC_eco_collect_country_statistics = yes\n'))
 # Daily totals remain exact, including damage and population changes; local
 # UI actions reuse today's rollup. Construction/control changes invalidate it.
 b='APDC_eco_ensure_country_statistics = yes\n'
 b+=calc('public_available','num_of_civilian_factories_available_for_projects',('add',var('public_civ')),('min','num_of_civilian_factories'),('max',0),('round','down'))
 b+='clamp_variable = { var = APDC_eco_public_civ min = 0 max = APDC_eco_public_available }\n'
 b+=calc('demand_m',mod('population_factor'),('add',1),('max',0),('multiply',var('population_base')),('multiply',var('population_m')))
 b+=calc('goods_per_civ_m',mod('civ_goods'),('multiply','{ value = modifier@industrial_capacity_factory add = 1 max = 0 }'),('multiply','{ value = '+mod('goods_output_factor')+' add = 1 max = 0 }'))
 b+=calc('domestic_m',var('public_civ'),('add',var('private_civ')),('multiply',var('goods_per_civ_m')))
 # The subsequent gap calculation replaces last_civ_capacity. Preserve the
 # operand consumed here for the UI; this snapshot never feeds settlement.
 b+=setv('distribution_capacity_input',var('last_civ_capacity'))
 b+=calc('distribution',var('last_civ_capacity'),('max',0),('min',50),('multiply',-.004),('add',.8),('add',mod('distribution_bonus')),('clamp','{ min = 0 max = 1 }'))
 b+=cond(P+'is_planned = yes',calc('distribution','political_power_daily',('multiply',.15),('add',.6),('clamp','{ min = 0 max = 1 }')))
 b+=calc('supply_m',var('domestic_m'),('add',var('extra_input')),('subtract',var('extra_output')),('max',0),('multiply',var('distribution')))
 b+=setv('import_target_m',0)+setv('export_target_m',0)
 b+=cond(check('demand_m','>',var('supply_m')),calc('import_target_m',var('demand_m'),('subtract',var('supply_m')),('multiply',var('trade_freedom'))),
  calc('export_target_m',var('supply_m'),('subtract',var('demand_m')),('multiply',var('trade_freedom'))))
 # Local actions reuse the active trade plan. Only a completed weekly plan
 # changes partners; daily validation can reduce or cancel existing flows.
 refresh='APDC_eco_calculate_country = yes\n'+calc('supply_m',var('domestic_m'),('add',var('extra_input')),('subtract',var('extra_output')),('add',var('imports_m')),('subtract',var('exports_m')),('max',0),('multiply',var('distribution')))+'APDC_eco_calculate_gap = yes\n'
 return statistics+effect('calculate_country',b)+effect('refresh_current_supply',refresh)

def build_trade():
 from build_market import build as build_market
 build_market()
 return ''


def build_growth():
 s=''
 b=setv('shortage',0)+setv('surplus',0)+setv('food_penalty',0)
 b+=cond(check('demand_m','>',0),calc('shortage',var('demand_m'),('subtract',var('supply_m')),('divide',var('demand_m')),('max',0))+calc('surplus',var('supply_m'),('subtract',var('demand_m')),('divide',var('demand_m')),('max',0)))
 b+=calc('food_penalty',var('shortage'),('min',1),('multiply',-.1))
 for kind in ['civ','mil']:
  c=calc(kind+'_capacity',mod(kind+'_expansion_base'),('multiply','{ value = modifier@production_speed_buildings_factor add = modifier@production_speed_'+('industrial_complex' if kind=='civ' else 'arms_factory')+'_factor add = 1 max = 0 }'),
   ('multiply','{ value = '+mod('private_'+kind+'_expansion_factor')+' add = 1 max = 0 }'),('multiply','{ value = APDC_eco_shortage add = 1 }'))
  c+=calc(kind+'_velocity',var(kind+'_capacity'),('multiply',var('private_civ')),('add',5),('multiply',.5))
  c+=cond(check('shortage','<=',.1)+' '+check('surplus','<=',.1),setv(kind+'_capacity',0)+setv(kind+'_velocity',0))
  c+=cond(check('surplus','>',.1),setv(kind+'_capacity',0)+calc(kind+'_velocity',var('surplus'),('multiply',var('private_civ')),('multiply',-2.5)))
  c+=cond(P+'is_planned = yes',setv(kind+'_capacity',0)+setv(kind+'_velocity',0))
  c+=cond(check(kind+'_velocity','>',0)+' NOT = { any_controlled_state = { free_building_slots = { building = '+P+'private_'+kind+' size > 0 } } }',setv(kind+'_capacity',0)+setv(kind+'_velocity',0))
  b+=c
 b+=setv('last_civ_capacity',var('civ_capacity'))
 s+=effect('calculate_gap',b)
 for kind,cost in [('civ',10800),('mil',7200)]:
  s+=effect('complete_'+kind,
   setv('build_done',0)+''.join(cond(check('build_done','=',0),
    'random_controlled_state = { limit = { '+test+' free_building_slots = { building = '+P+'private_'+kind+' size > 0 } }\n'
    'add_building_construction = { type = '+P+'private_'+kind+' level = 1 instant_build = yes }\nPREV = { clr_country_flag = APDC_eco_statistics_today }\nset_variable = { PREV.APDC_eco_build_done = 1 }\n}\n')
    for test in ['is_owned_by = PREV is_core_of = PREV','is_owned_by = PREV NOT = { is_core_of = PREV }','NOT = { is_owned_by = PREV }']))
  state_remove=(
   # These hidden buildings have no construction-unlocking technology. The
   # native setter clamps positive levels to the tech cap (zero), so preserve
   # N-1 levels through the verified instant-construction path after clearing.
   'set_temp_variable = { APDC_eco_saved_damage = damaged_building_level@'+P+'private_'+kind+' }\n'
   +''.join(cond('check_variable = { building_level@'+P+'private_'+kind+' = '+str(level)+' }',
    'set_building_level = { type = '+P+'private_'+kind+' level = 0 }\n'+
    (('add_building_construction = { type = '+P+'private_'+kind+' level = '+str(level-1)+' instant_build = yes }\n') if level>1 else '')+
    'clamp_temp_variable = { var = APDC_eco_saved_damage min = 0 max = '+str(level-1)+' }\n'
    'PREV = { clr_country_flag = APDC_eco_statistics_today }\nset_variable = { PREV.APDC_eco_demolish_done = 1 }\n') for level in range(1,51)))
  # damage_building accepts literal numbers only. Restore the saved damage
  # with binary-denominated literal amounts at the engine's 5-decimal precision.
  for bit in reversed(range(23)):
   damage=format((2**bit)/100000,'.5f')
   state_remove+=cond('NOT = { check_variable = { APDC_eco_saved_damage < '+damage+' } }',
    'damage_building = { type = '+P+'private_'+kind+' damage = '+damage+' }\nsubtract_from_temp_variable = { APDC_eco_saved_damage = '+damage+' }\n')
  s+=effect('demolish_'+kind+'_in_state',state_remove)
  s+=effect('demolish_'+kind,setv('demolish_done',0)+'random_controlled_state = { limit = { check_variable = { building_level@'+P+'private_'+kind+' > 0 } } APDC_eco_demolish_'+kind+'_in_state = yes }\n')
  b=add(kind+'_progress',var(kind+'_velocity'))
  b+=setv('construction_continue',1)+'while_loop_effect = { limit = { '+check('construction_continue','=',1)+' '+check(kind+'_progress','>=',cost)+' }\nAPDC_eco_complete_'+kind+' = yes\n'+cond(check('build_done','=',1),add(kind+'_progress',-cost),setv(kind+'_progress',cost)+setv('construction_continue',0))+'}\n'
  # A zero crossing removes one factory immediately, then carries a reverse
  # construction-cost remainder until the following removal, as specified.
  b+=cond(check(kind+'_velocity','<',0),
   setv('construction_continue',1)+'while_loop_effect = { limit = { '+check('construction_continue','=',1)+' '+check(kind+'_progress','<=',0)+' }\nAPDC_eco_demolish_'+kind+' = yes\n'+cond(check('demolish_done','=',1),add(kind+'_progress',cost),setv(kind+'_progress',0)+setv('construction_continue',0))+'}\n')
  s+=effect('advance_'+kind,b)
 return s

def build_planned():
 b='APDC_eco_initialize_stock_arrays = yes\n'+cond(P+'is_planned = yes',
  cond('OR = { NOT = { has_idea = APDC_eco_distribution_5 } has_idea = APDC_eco_distribution_1 has_idea = APDC_eco_distribution_2 has_idea = APDC_eco_distribution_3 has_idea = APDC_eco_distribution_4 }',
   'remove_ideas = APDC_eco_distribution_1\nremove_ideas = APDC_eco_distribution_2\nremove_ideas = APDC_eco_distribution_3\nremove_ideas = APDC_eco_distribution_4\nadd_ideas = APDC_eco_distribution_5\n')+
  cond('OR = { NOT = { has_country_flag = APDC_eco_planned_normalized } has_country_flag = APDC_eco_private_stock_dirty '+check('private_civ_raw','>',0)+' '+check('private_mil_raw','>',0)+' }',
  'every_controlled_state = {\n'+''.join(
   f'set_temp_variable = {{ APDC_eco_convert = building_level@APDC_eco_private_{k} }}\n'
   f'if = {{ limit = {{ check_variable = {{ APDC_eco_convert > 0 }} }} set_building_level = {{ type = APDC_eco_private_{k} level = 0 }} '
   f'add_building_construction = {{ type = {native} level = APDC_eco_convert instant_build = yes }} }}\n'
   for k,native in [('civ','industrial_complex'),('mil','arms_factory')])+'}\nAPDC_eco_nationalize_stock = yes\nclr_country_flag = APDC_eco_statistics_today\nset_country_flag = APDC_eco_planned_normalized\n'+setv('civ_progress',0)+setv('mil_progress',0)),
  'clr_country_flag = APDC_eco_planned_normalized\n'+cond('has_idea = APDC_eco_distribution_5','remove_ideas = APDC_eco_distribution_5\nadd_ideas = APDC_eco_distribution_1\n'))
 return effect('reconcile_planned',b)

def build_budget():
 # The first getter excludes factories assigned to the construction queue;
 # the second includes them. Verified against a live 15-CIV construction line.
 b=calc('construction_civ','num_of_civilian_factories_available_for_projects',('subtract','num_of_available_civilian_factories'),('max',0))
 b+=calc('working_mil','num_of_military_factories',('subtract','num_of_available_military_factories'),('max',0))
 b+=calc('working_nav','num_of_naval_factories',('subtract','num_of_available_naval_factories'),('max',0))
 research=setv('research_active',0)+setv('project_active',0)
 # Enumerate actual research subjects, never total or unlocked slot capacity.
 techs=set()
 for p in effective_files('common/technologies'):
  for n in parse(p.read_text('utf-8-sig')):
   if n.key=='technologies': techs.update(x.key for x in n.children if x.value is None)
 for t in sorted(techs): research+=cond('is_researching_technology = '+t,add('research_active',1))
 for p in effective_files('common/special_projects/projects'):
  for n in parse(p.read_text('utf-8-sig')):
   if n.value is None: research+=cond('is_special_project_being_researched = sp:'+n.key,add('project_active',1))
 research+='set_country_flag = { flag = APDC_eco_research_counted_today value = 1 days = 1 }\n'
 b+=cond('NOT = { has_country_flag = APDC_eco_research_counted_today }','APDC_eco_count_research_work = yes\n')
 b+=calc('head_tax_m',var('population_m'),('multiply',mod('head_tax')))
 b+=calc('consumption_tax_m',var('supply_m'),('multiply',mod('consumption_tax')))
 b+=calc('subsidies_m',var('supply_m'),('multiply',mod('subsidy')))
 b+=calc('welfare_cost_m',mod('food_cost'),('add',mod('education_cost')),('add',mod('medical_cost')),('multiply',var('population_m')))
 b+=calc('investment_cost_m',var('public_civ'),('add',var('private_civ')),('multiply',mod('investment_cost')))
 for name,count,base,factor in [('construction','construction_civ','construction_maintenance','construction_maintenance_factor'),('production','working_mil','mil_maintenance','mil_maintenance_factor'),('naval_production','working_nav','nav_maintenance','nav_maintenance_factor'),('research','research_active','research_maintenance','research_maintenance_factor'),('projects','project_active','project_maintenance','project_maintenance_factor')]:
  b+=calc(name+'_cost_m',mod(base),('multiply',var(count)),('multiply','{ value = '+mod(factor)+' add = 1 max = 0 }'))
 for kind in ['army','navy','air']:
  manpower={'army':'deployed_army_manpower_k','navy':'deployed_navy_manpower_k','air':'deployed_airforce_manpower_k'}[kind]
  b+=calc(kind+'_personnel_m',manpower,('divide',1000))
 b+=calc('army_personnel_m',var('army_personnel_m'),('add','{ value = amount_manpower_in_deployment_queue divide = 1000000 }'))
 # User decision 2026-10-23: exclude occupation garrisons. The native getter
 # reports required establishment, not actual filled personnel.
 b+=setv('garrison_personnel_m',0)
 for kind in ['army','navy','air']:
  b+=calc(kind+'_cost_m',var(kind+'_personnel_m'),('multiply',mod(kind+'_maintenance')),('multiply','{ value = '+mod(kind+'_maintenance_factor')+' add = 1 max = 0 }'))
 b+=calc('weekly_income_m',var('head_tax_m'),('add',var('consumption_tax_m')),('add',var('tariffs_m')))
 expenses=['subsidies','welfare_cost','investment_cost','construction_cost','production_cost','naval_production_cost','research_cost','projects_cost','army_cost','navy_cost','air_cost']
 b+=calc('weekly_expenses_m',0,*[('add',var(n+'_m')) for n in expenses])
 b+=calc('weekly_balance_m',var('weekly_income_m'),('subtract',var('weekly_expenses_m')))
 b+=calc('cash_display_m',var('cash_k'),('divide',1000),('add',var('cash_m')))
 s=effect('count_research_work',research)+effect('calculate_budget',b)
 s+=effect('normalize_cash',calc('cash_carry',var('cash_k'),('divide',1000),('round','down'))+add('cash_m',var('cash_carry'))+calc('cash_k',var('cash_carry'),('multiply',-1000),('add',var('cash_k'))))
 b='clr_country_flag = APDC_eco_research_counted_today\nAPDC_eco_calculate_budget = yes\n'+calc('weekly_whole',var('weekly_balance_m'),('round','down'))+calc('weekly_fraction',var('weekly_balance_m'),('subtract',var('weekly_whole')),('multiply',1000))
 b+=add('cash_m',var('weekly_whole'))+add('cash_k',var('weekly_fraction'))+'APDC_eco_normalize_cash = yes\nAPDC_eco_bankruptcy = yes\n'
 for k,*_ in TRACKS:
  b+=add(k,mod(k+'_weekly'))
  if k=='food': b+=add(k,var('food_penalty'))
 b+='APDC_eco_sync_development = yes\nAPDC_eco_refresh_policies = yes\n'+add('week_ticks',1)
 s+=effect('settle_week',b)
 return s

def build(runtime_only=True):
 if runtime_only:
  import json
  data=json.loads((WORK/'design_data.json').read_text('utf-8'))
 else:
  data=build_data();build_migration();adapt_system_api()
 s=build_laws(data)+build_initialize()+build_country()+build_trade()+build_growth()+build_planned()+build_budget()
 s+=effect('assign_validation_cohort',cond('NOT = { has_variable = APDC_eco_validation_cohort }',setv('validation_cohort','global.APDC_eco_next_cohort')+'add_to_variable = { global.APDC_eco_next_cohort = 1 }\nmodulo_variable = { global.APDC_eco_next_cohort = 7 }\n'))
 s+=effect('daily_country','APDC_eco_initialize_country = yes\nAPDC_eco_assign_validation_cohort = yes\nclr_country_flag = APDC_eco_statistics_today\nclr_country_flag = APDC_eco_research_counted_today\n'+cond(check('validation_cohort','=','global.APDC_eco_validation_day'),'set_country_flag = APDC_eco_equipment_dirty\nclr_country_flag = APDC_eco_planned_normalized\n')+'APDC_eco_ensure_equipment = yes\nAPDC_eco_ensure_country_statistics = yes\nAPDC_eco_reconcile_planned = yes\nAPDC_eco_refresh_policies = yes\nAPDC_eco_bankruptcy = yes\nAPDC_eco_calculate_country = yes\n')
 # Cash is settled weekly using that day's laws. Only an open human panel
 # needs a daily projection; action APIs and weekly settlement refresh it.
 s+=effect('daily_after_market','APDC_eco_advance_civ = yes\nAPDC_eco_advance_mil = yes\nAPDC_eco_produce_equipment = yes\n'+add('day_ticks',1)+cond('is_ai = no has_variable = APDC_eco_panel_open','APDC_eco_calculate_budget = yes\nAPDC_eco_sync_ui = yes'))
 write('common/scripted_effects/APDC_economy_backend.txt',s)
 # Generic on_daily/on_weekly fire in country scopes. A global date guard
 # runs world matching once, including when the initially selected tag changes.
 startup='every_country = { APDC_eco_initialize_country = yes }\nevery_country = { APDC_eco_calculate_country = yes }\nevery_country = { limit = { NOT = { has_global_flag = APDC_eco_market_v2_ready } } APDC_eco_market_bootstrap = yes }\n'
 daily=cond('NOT = { has_global_flag = APDC_eco_daily_tick_lock }',
  'set_global_flag = { flag = APDC_eco_daily_tick_lock value = 1 days = 1 }\nevery_country = { APDC_eco_daily_country = yes }\nAPDC_eco_market_bootstrap = yes\nAPDC_eco_validate_world_trade = yes\nAPDC_eco_market_daily = yes\nevery_country = { APDC_eco_daily_after_market = yes }\nadd_to_variable = { global.APDC_eco_validation_day = 1 }\nmodulo_variable = { global.APDC_eco_validation_day = 7 }\n')
 weekly=cond('NOT = { has_global_flag = APDC_eco_weekly_tick_lock }',
  'set_global_flag = { flag = APDC_eco_weekly_tick_lock value = 1 days = 7 }\nevery_country = { APDC_eco_settle_week = yes }\nAPDC_eco_clear_world_market = yes\n')
 control='ROOT = { clr_country_flag = APDC_eco_statistics_today clr_country_flag = APDC_eco_planned_normalized }\nFROM = { clr_country_flag = APDC_eco_statistics_today clr_country_flag = APDC_eco_planned_normalized }\n'
 war=cond('has_global_flag = APDC_eco_market_v2_ready','APDC_eco_validate_world_trade = yes\n')
 write('common/on_actions/zz_APDC_economy.txt',block('on_actions',block('on_startup',block('effect',startup))+block('on_daily',block('effect',daily))+block('on_weekly',block('effect',weekly))+block('on_state_control_changed',block('effect',control))+block('on_war_relation_added',block('effect',war))))
 print('Economy backend generated')

if __name__=='__main__':
 import sys
 build(runtime_only='--migrate' not in sys.argv)
