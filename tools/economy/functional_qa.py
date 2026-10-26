"""Engine-side behavioral assertions, installed only in the isolated QA overlay."""
import json
from common import *
from build_backend import effect, var, add
from runtime import QA

def assertion(name, test):
 return cond(test,'log = "APDC_ECO_ASSERT PASS '+name+'"','log = "APDC_ECO_ASSERT FAIL '+name+'"')

def laws(key, tier):
 return ''.join('remove_ideas = APDC_eco_'+key+'_'+str(j)+'\n' for j in range(1,6))+'add_ideas = APDC_eco_'+key+'_'+str(tier)+'\n'

def build():
 items=json.loads((WORK/'equipment_catalogue.json').read_text('utf-8'))
 e=next(x for x in items if x['id']=='infantry_equipment_0'); i=e['index']
 b='set_variable = { global.APDC_eco_qa_trade_delta = 0 }\nevery_country = { add_to_variable = { global.APDC_eco_qa_trade_delta = APDC_eco_imports_m } subtract_from_variable = { global.APDC_eco_qa_trade_delta = APDC_eco_exports_m } }\n'
 b+=assertion('world_trade_conservation','check_variable = { global.APDC_eco_qa_trade_delta > -0.001 } check_variable = { global.APDC_eco_qa_trade_delta < 0.001 }')
 b+='every_country = { set_variable = { APDC_eco_import_target_m = 0 } set_variable = { APDC_eco_export_target_m = 0 } }\n'+setv('export_target_m',5)+setv('tariff',1)+'FRA = { set_variable = { APDC_eco_import_target_m = 10 } set_variable = { APDC_eco_tariff = 2.5 } }\nAPDC_eco_clear_world_market = yes\n'
 b+=assertion('paired_trade_and_export_tariff',check('exports_m','=',5)+' '+check('tariffs_m','=',5))
 b+='FRA = { '+assertion('paired_trade_and_import_tariff',check('imports_m','=',5)+' '+check('tariffs_m','=',12.5))+' }\n'
 b+=setv('cash_m',10)+setv('cash_k',0)+setv('stock_'+str(i),10)+setv('purchase_id',i)+setv('purchase_quantity',2)
 b+='APDC_eco_purchase_equipment = yes\n'
 b+='log = "APDC_ECO_DIAG PURCHASE stock=[?APDC_eco_stock_'+str(i)+'] cash=[?APDC_eco_cash_m] lower=[?APDC_eco_cash_k] quantity=[?APDC_eco_purchase_quantity] unit=[?APDC_eco_purchase_unit_k] cost_m=[?APDC_eco_purchase_cost_m] cost_k=[?APDC_eco_purchase_cost_k]"\n'
 b+=assertion('purchase_exact_172_rubles',check('stock_'+str(i),'=',8)+' '+check('cash_m','=',9)+' '+check('cash_k','=',999.828))
 b+=setv('cash_m',0)+setv('cash_k',0)+setv('purchase_quantity',1)+'APDC_eco_purchase_equipment = yes\n'
 b+=assertion('purchase_insufficient_funds_no_change',check('stock_'+str(i),'=',8)+' '+check('cash_m','=',0)+' '+check('cash_k','=',0))
 b+=laws('tax',5)+laws('investment',5)+laws('distribution',4)+laws('consumption',5)+setv('cash_m',-1)+'APDC_eco_bankruptcy = yes\n'
 b+=assertion('bankruptcy_spending_only','has_idea = APDC_eco_tax_5 has_idea = APDC_eco_investment_1 has_idea = APDC_eco_distribution_1 has_idea = APDC_eco_consumption_3')
 b+=setv('selected_group',1)+setv('requested_law',2)+'add_political_power = 1000\n'+setv('qa_pp_before','political_power')+'APDC_eco_change_law = yes\n'
 b+=assertion('negative_treasury_law_lock','has_idea = APDC_eco_tax_5 '+check('qa_pp_before','=','political_power'))
 b+=setv('cash_m',10)+'APDC_eco_change_law = yes\n'+calc('qa_pp_spent',var('qa_pp_before'),('subtract','political_power'))
 b+=assertion('law_switch_150pp','has_idea = APDC_eco_tax_2 NOT = { has_idea = APDC_eco_tax_5 } '+check('qa_pp_spent','=',150))
 b+=setv('imports_m',10)+setv('exports_m',0)+'APDC_eco_refresh_current_supply = yes\n'+calc('qa_supply',var('domestic_m'),('add',var('extra_input')),('subtract',var('extra_output')),('add',10),('max',0),('multiply',var('distribution')))
 b+=assertion('local_action_retains_imports',check('supply_m','=',var('qa_supply')))
 b+='APDC_eco_calculate_country = yes\n'+setv('qa_civ_before',var('private_civ_raw'))+setv('civ_progress',21723)+setv('civ_velocity',0)+'APDC_eco_advance_civ = yes\nAPDC_eco_calculate_country = yes\n'+calc('qa_built',var('private_civ_raw'),('subtract',var('qa_civ_before')))
 b+=assertion('continuous_construction_two_and_carry',check('qa_built','=',2)+' '+check('civ_progress','=',123))
 b+=setv('qa_civ_before',var('private_civ_raw'))+setv('civ_velocity',-124)+'APDC_eco_advance_civ = yes\nAPDC_eco_calculate_country = yes\n'+calc('qa_removed',var('qa_civ_before'),('subtract',var('private_civ_raw')))
 b+='log = "APDC_ECO_DIAG DEMOLITION before=[?APDC_eco_qa_civ_before] after=[?APDC_eco_private_civ_raw] removed=[?APDC_eco_qa_removed] progress=[?APDC_eco_civ_progress]"\n'
 b+=assertion('demolition_zero_cross_and_carry',check('qa_removed','=',1)+' '+check('civ_progress','=',10799))
 b+=setv('civ_progress',100)+setv('civ_velocity',-21701)+setv('qa_civ_before',var('private_civ_raw'))+'APDC_eco_advance_civ = yes\nAPDC_eco_calculate_country = yes\n'+calc('qa_removed',var('qa_civ_before'),('subtract',var('private_civ_raw')))
 b+='log = "APDC_ECO_DIAG MULTI_DEMOLITION before=[?APDC_eco_qa_civ_before] after=[?APDC_eco_private_civ_raw] removed=[?APDC_eco_qa_removed] progress=[?APDC_eco_civ_progress]"\n'
 b+=assertion('continuous_demolition_three_and_carry',check('qa_removed','=',3)+' '+check('civ_progress','=',10799))
 b+=setv('qa_civ_before',var('private_civ_raw'))+'for_loop_effect = { start = 1 end = 20 compare = less_than_or_equals value = APDC_eco_qa_iteration APDC_eco_complete_civ = yes APDC_eco_calculate_country = yes log = "APDC_ECO_PAIR BUILD step=[?APDC_eco_qa_iteration] count=[?APDC_eco_private_civ_raw]" APDC_eco_demolish_civ = yes APDC_eco_calculate_country = yes log = "APDC_ECO_PAIR DEMOLISH step=[?APDC_eco_qa_iteration] count=[?APDC_eco_private_civ_raw] done=[?APDC_eco_demolish_done]" }\nAPDC_eco_calculate_country = yes\n'
 b+='log = "APDC_ECO_PAIR RESULT before=[?APDC_eco_qa_civ_before] after=[?APDC_eco_private_civ_raw]"\n'
 b+=assertion('twenty_random_build_demolish_pairs',check('private_civ_raw','=',var('qa_civ_before')))
 b+='64 = { add_building_construction = { type = APDC_eco_private_civ level = 3 instant_build = yes } damage_building = { type = APDC_eco_private_civ damage = 1.4 } set_variable = { PREV.APDC_eco_qa_damage_before = damaged_building_level@APDC_eco_private_civ } set_variable = { PREV.APDC_eco_qa_level_before = building_level@APDC_eco_private_civ } APDC_eco_demolish_civ_in_state = yes set_variable = { PREV.APDC_eco_qa_damage_after = damaged_building_level@APDC_eco_private_civ } set_variable = { PREV.APDC_eco_qa_level_after = building_level@APDC_eco_private_civ } }\n'
 b+=calc('qa_damage_delta',var('qa_damage_before'),('subtract',var('qa_damage_after')))+calc('qa_level_delta',var('qa_level_before'),('subtract',var('qa_level_after')))
 b+=assertion('damaged_factory_removal_preserves_damage',check('qa_level_delta','=',1)+' '+check('qa_damage_delta','<',.0001)+' '+check('qa_damage_delta','>',-.0001))
 b+=setv('demand_m',100)+setv('supply_m',90)+'APDC_eco_calculate_gap = yes\n'
 b+=assertion('neutral_band_lower',check('civ_velocity','=',0)+' '+check('mil_velocity','=',0)+' '+check('food_penalty','=',-.01))
 b+=setv('supply_m',110)+'APDC_eco_calculate_gap = yes\n'
 b+=assertion('neutral_band_upper',check('civ_velocity','=',0)+' '+check('mil_velocity','=',0))
 b+=setv('private_civ',0)+setv('supply_m',50)+'APDC_eco_calculate_gap = yes\n'
 b+=assertion('white_base_five_half_each',check('civ_velocity','=',2.5)+' '+check('mil_velocity','=',2.5))
 b+=setv('qa_income_before',0)+'APDC_eco_refresh_current_supply = yes\nAPDC_eco_calculate_budget = yes\n'
 b+=calc('qa_tax',var('supply_m'),('multiply','modifier@APDC_eco_consumption_tax'))
 b+=assertion('consumption_tax_final_supply',check('consumption_tax_m','=',var('qa_tax')))
 b+='log = "APDC_ECO_DIAG FACTORIES all=[?num_of_civilian_factories] free=[?num_of_available_civilian_factories] projects=[?num_of_civilian_factories_available_for_projects] active=[?APDC_eco_construction_civ] allocated=[?APDC_eco_public_civ]"\n'
 # A real construction queue: no instant-build, no main-project history edits.
 b+='64 = { add_building_construction = { type = industrial_complex level = 1 instant_build = no } }\n57 = { add_core_of = FRA remove_core_of = GER }\nFRA = { transfer_state = 57 }\nset_state_controller = 57\n57 = { set_resistance = 30 set_garrison_strength = 0.5 }\n'
 b+='add_equipment_production = { equipment = { type = infantry_equipment_0 creator = GER } requested_factories = 2 }\n'
 b+='APDC_eco_calculate_country = yes\n'
 b+='set_technology = { gwtank_chassis = 1 basic_light_tank_chassis = 1 engines_1 = 1 iw_small_airframe = 1 }\nAPDC_eco_refresh_equipment = yes\n'
 b+=setv('food',5.8)+'APDC_eco_sync_development = yes\n'+assertion('development_upper_clamp',check('food','=',5)+' has_idea = APDC_eco_food_5')
 b+=setv('food',.7)+'APDC_eco_sync_development = yes\n'+assertion('development_lower_clamp',check('food','=',1)+' has_idea = APDC_eco_food_1')
 b+=setv('food',3)+'APDC_eco_sync_development = yes\n'
 s=effect('qa_fixtures',b)
 diag='''log = "APDC_ECO_DIAG COUNTS date=[GetDateText] all=[?num_of_civilian_factories] free=[?num_of_available_civilian_factories] projects=[?num_of_civilian_factories_available_for_projects] active=[?APDC_eco_construction_civ] mil=[?APDC_eco_working_mil] max=[?max_manpower_k] available=[?max_available_manpower_k] pool=[?manpower_k] total=[?deployed_total_manpower_k] army=[?deployed_army_manpower_k] navy=[?deployed_navy_manpower_k] air=[?deployed_airforce_manpower_k] training=[?amount_manpower_in_deployment_queue] garrison_need=[?garrison_manpower_need] foreign=[?foreign_manpower] native_cg=[?modifier@consumer_goods_expected_value] native_factor=[?modifier@consumer_goods_factor]"\n'''
 b='APDC_eco_calculate_country = yes\n'+setv('qa_civ_before',var('private_civ_raw'))+setv('qa_mil_before',var('private_mil_raw'))
 # Sum raw native buildings, not the rounded national effective factory count.
 b+=setv('qa_native_before',0)+'every_controlled_state = { add_to_variable = { PREV.APDC_eco_qa_native_before = building_level@industrial_complex } add_to_variable = { PREV.APDC_eco_qa_native_before = building_level@arms_factory } }\n'
 b+=setv('stock_'+str(i),8)
 for name in ['traditional_agriculture','dependent_economy','free_market','mixed_market','state_guided','state_capitalism','market_socialism','decentralized_planning','central_planning']:
  b+='remove_ideas = APDC_economic_system_'+name+'_idea\n'
 b+='add_ideas = APDC_economic_system_central_planning_idea\nAPDC_eco_reconcile_planned = yes\nAPDC_eco_calculate_country = yes\n'
 b+=setv('qa_native_after',0)+'every_controlled_state = { add_to_variable = { PREV.APDC_eco_qa_native_after = building_level@industrial_complex } add_to_variable = { PREV.APDC_eco_qa_native_after = building_level@arms_factory } }\n'
 b+=calc('qa_converted',var('qa_native_after'),('subtract',var('qa_native_before')),('subtract',var('qa_civ_before')),('subtract',var('qa_mil_before')))
 b+=assertion('planned_conversion_conserves_buildings',check('qa_converted','=',0)+' '+check('private_civ_raw','=',0)+' '+check('private_mil_raw','=',0)+' has_idea = APDC_eco_distribution_5')
 b+=assertion('planned_stock_transfer',check('stock_'+str(i),'=',0))
 b+=setv('cash_m',-1)+'APDC_eco_bankruptcy = yes\n'
 b+=assertion('planned_bankruptcy_preserves_distribution','has_idea = APDC_eco_distribution_5')
 s+=effect('qa_planned',b)
 write_path=QA/'driver/common/scripted_effects/APDC_economy_qa.txt'
 write_path.write_text(lower_math(s),'utf-8')
 on='on_actions = { on_daily_GER = { effect = {\n'
 on+=cond('date > 2060.1.3 NOT = { has_country_flag = APDC_eco_qa_tested }','set_country_flag = APDC_eco_qa_tested\nAPDC_eco_qa_fixtures = yes\n')
 on+=cond('date > 2060.1.4',diag)
 on+=cond('date > 2060.1.6 NOT = { has_country_flag = APDC_eco_qa_full_garrison }','set_country_flag = APDC_eco_qa_full_garrison\n57 = { set_garrison_strength = 1 }\n64 = { create_unit = { division = "name = \\"APDC QA infantry\\" division_template = \\"六营步兵师\\" start_manpower_factor = 1 start_equipment_factor = 0" owner = GER } }\n'.replace('\\\\"','\\"'))
 on+=cond('date > 2060.1.10 NOT = { has_country_flag = APDC_eco_qa_plan_tested }','set_country_flag = APDC_eco_qa_plan_tested\nAPDC_eco_qa_planned = yes\n')
 on+=cond('date > 2060.1.12 NOT = { has_country_flag = APDC_eco_qa_manpower_audit }','set_country_flag = APDC_eco_qa_manpower_audit\nlog = "APDC_ECO_MANPOWER BEFORE available=[?max_available_manpower_k] pool=[?manpower_k] total=[?deployed_total_manpower_k]"\nadd_manpower = -6000\nlog = "APDC_ECO_MANPOWER AFTER available=[?max_available_manpower_k] pool=[?manpower_k] total=[?deployed_total_manpower_k]"\n')
 on+=cond('date > 2060.2.2 NOT = { has_country_flag = APDC_eco_qa_mobilization }','set_country_flag = APDC_eco_qa_mobilization\nremove_ideas = volunteer_only\nremove_ideas = limited_conscription\nremove_ideas = extensive_conscription\nadd_ideas = service_by_requirement\n')
 on+='} } }\n'
 (QA/'driver/common/on_actions/zzzz_APDC_economy_qa_fixtures.txt').write_text(on,'utf-8')
 print('Installed behavioral QA in isolated overlay only; infantry catalogue ID',i)

if __name__=='__main__':build()
