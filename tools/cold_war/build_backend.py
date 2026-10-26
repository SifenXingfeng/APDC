"""Sparse country control data, proportional changes and event-facing interfaces."""
import json
from common import ROOT, OUT, block, iff, setv, add, write

AXES=('political','economic','military')

def build():
    effects={}
    init='''if = { limit = { NOT = { has_country_flag = apdc_cw_initialized } }
set_country_flag = apdc_cw_initialized
add_to_array = { array = apdc_cw_sources value = THIS }
set_variable = { apdc_cw_status = 4 }
'''
    for a in AXES:
        init+=f'add_to_array = {{ array = apdc_cw_{a} value = 100 }}\n'
        init+=f'add_to_array = {{ array = apdc_cw_old_{a} value = 100 }}\nadd_to_array = {{ array = apdc_cw_law_delta_{a} value = 0 }}\n'
    init+='add_to_array = { array = apdc_cw_auto_delta value = 0 }\n'
    init+='}\n'
    effects['apdc_cw_ensure']=init
    effects['apdc_cw_notify_controls']='every_country = { limit = { is_ai = no has_country_flag = apdc_cw_open } apdc_cw_refresh_view = yes }'
    effects['apdc_cw_invalidate_maps']='''add_to_variable = { global.apdc_cw_map_revision = 1 }
every_country = { limit = { is_ai = no has_country_flag = apdc_cw_open }
apdc_cw_refresh_world = yes
if = { limit = { check_variable = { apdc_cw_detail = 1 } } apdc_cw_prepare_detail = yes }
apdc_cw_refresh_view = yes
}'''
    effects['apdc_cw_register_active_target']=iff('NOT = { is_in_array = { array = global.apdc_cw_active_targets value = THIS } }','add_to_array = { array = global.apdc_cw_active_targets value = THIS }')
    effects['apdc_cw_find_source']='''set_variable = { apdc_cw_source_index = -1 }
for_each_loop = { array = apdc_cw_sources value = apdc_cw_source_value index = apdc_cw_source_cursor
if = { limit = { var:apdc_cw_source_value = { tag = var:PREV.apdc_cw_actor } }
set_variable = { apdc_cw_source_index = apdc_cw_source_cursor }
} }
'''
    effects['apdc_cw_ensure_source']='''apdc_cw_ensure = yes
apdc_cw_find_source = yes
if = { limit = { check_variable = { apdc_cw_source_index < 0 } }
set_variable = { apdc_cw_source_index = apdc_cw_sources^num }
add_to_array = { array = apdc_cw_sources value = var:apdc_cw_actor }
'''+''.join(f'add_to_array = {{ array = apdc_cw_{a} value = 0 }}\nadd_to_array = {{ array = apdc_cw_old_{a} value = 0 }}\nadd_to_array = {{ array = apdc_cw_law_delta_{a} value = 0 }}\n' for a in AXES)+'''add_to_array = { array = apdc_cw_auto_delta value = 0 }
}
apdc_cw_register_active_target = yes
'''
    for a in AXES:
        # Ordinary direct changes behave like adding/removing ideology support:
        # preserve the selected share, scale every other share to the remainder.
        s=f'''set_temp_variable = {{ apdc_cw_old = apdc_cw_{a}^apdc_cw_source_index }}
set_temp_variable = {{ apdc_cw_new = apdc_cw_old }}
add_to_temp_variable = {{ apdc_cw_new = apdc_cw_delta }}
clamp_temp_variable = {{ var = apdc_cw_new min = 0 max = 100 }}
set_temp_variable = {{ apdc_cw_rest = 100 }}
subtract_from_temp_variable = {{ apdc_cw_rest = apdc_cw_old }}
if = {{ limit = {{ check_variable = {{ apdc_cw_rest > 0 }} }}
set_temp_variable = {{ apdc_cw_factor = 100 }}
subtract_from_temp_variable = {{ apdc_cw_factor = apdc_cw_new }}
set_temp_variable = {{ apdc_cw_total = apdc_cw_new }}
set_temp_variable = {{ apdc_cw_largest = -1 }}
set_temp_variable = {{ apdc_cw_remainder_index = 0 }}
for_loop_effect = {{ start = 0 end = apdc_cw_sources^num value = apdc_cw_j
if = {{ limit = {{ NOT = {{ check_variable = {{ apdc_cw_j = apdc_cw_source_index }} }} }}
multiply_variable = {{ apdc_cw_{a}^apdc_cw_j = apdc_cw_factor }}
divide_variable = {{ apdc_cw_{a}^apdc_cw_j = apdc_cw_rest }}
add_to_temp_variable = {{ apdc_cw_total = apdc_cw_{a}^apdc_cw_j }}
if = {{ limit = {{ check_variable = {{ apdc_cw_{a}^apdc_cw_j > apdc_cw_largest }} }}
set_temp_variable = {{ apdc_cw_largest = apdc_cw_{a}^apdc_cw_j }}
set_temp_variable = {{ apdc_cw_remainder_index = apdc_cw_j }}
}} }} }}
set_variable = {{ apdc_cw_{a}^apdc_cw_source_index = apdc_cw_new }}
set_temp_variable = {{ apdc_cw_rounding = 100 }}
subtract_from_temp_variable = {{ apdc_cw_rounding = apdc_cw_total }}
add_to_variable = {{ apdc_cw_{a}^apdc_cw_remainder_index = apdc_cw_rounding }}
}}
else_if = {{ limit = {{ NOT = {{ check_variable = {{ apdc_cw_source_index = 0 }} }} }}
set_variable = {{ apdc_cw_{a}^apdc_cw_source_index = apdc_cw_new }}
set_variable = {{ apdc_cw_{a}^0 = 100 }}
subtract_from_variable = {{ apdc_cw_{a}^0 = apdc_cw_new }}
}}
add_to_variable = {{ apdc_cw_revision = 1 }}
'''
        effects['apdc_cw_change_'+a]=s
    effects['apdc_cw_change_control']='apdc_cw_ensure_source = yes\n'+''.join(iff(f'check_variable = {{ apdc_cw_axis = {i} }}',f'apdc_cw_change_{a} = yes') for i,a in enumerate(AXES,1))+iff('NOT = { has_global_flag = apdc_cw_ticking }','apdc_cw_notify_controls = yes')
    for array,api in [('intervenable','intervention'),('controlled','controlled')]:
        effects['apdc_cw_set_'+api]=f'''if = {{ limit = {{ has_variable = apdc_cw_target }}
if = {{ limit = {{ is_in_array = {{ array = apdc_cw_{array} value = var:apdc_cw_target }} }} remove_from_array = {{ array = apdc_cw_{array} value = var:apdc_cw_target }} }}
if = {{ limit = {{ check_variable = {{ apdc_cw_value = 1 }} }} add_to_array = {{ array = apdc_cw_{array} value = var:apdc_cw_target }} }}
apdc_cw_invalidate_maps = yes
}}'''
    effects['apdc_cw_set_status']='set_variable = { apdc_cw_status = apdc_cw_value }\nadd_to_variable = { apdc_cw_revision = 1 }\napdc_cw_notify_controls = yes'
    # Runtime records are per owner/target/law. Definitions are generated from laws.json.
    # Preserve the existing saved array as the one shared switch cost.
    fields=['id','target','axis','beneficiary','rate','execute_cost','self','locked']
    effects['apdc_cw_find_law']='''set_variable = { apdc_cw_law_index = -1 }
for_each_loop = { array = apdc_cw_law_id value = apdc_cw_record_id index = apdc_cw_record_index
if = { limit = { check_variable = { apdc_cw_record_id = apdc_cw_id } var:apdc_cw_law_target^apdc_cw_record_index = { tag = var:PREV.apdc_cw_target } }
set_variable = { apdc_cw_law_index = apdc_cw_record_index }
} }
'''
    effects['apdc_cw_register_law']='''apdc_cw_ensure = yes
apdc_cw_find_law = yes
if = { limit = { check_variable = { apdc_cw_law_index < 0 } }
set_variable = { apdc_cw_law_index = apdc_cw_law_id^num }
'''+''.join(f'add_to_array = {{ array = apdc_cw_law_{f} value = var:apdc_cw_{f} }}\n' for f in fields)+'''
add_to_array = { array = apdc_cw_law_running value = 0 }
add_to_array = { array = apdc_cw_law_unlocked value = 1 }
add_to_array = { array = apdc_cw_law_last_delta value = 0 }
} else = { set_variable = { apdc_cw_law_unlocked^apdc_cw_law_index = 1 } }
if = { limit = { NOT = { is_in_array = { array = global.apdc_cw_law_owners value = THIS } } }
add_to_array = { array = global.apdc_cw_law_owners value = THIS } }
var:apdc_cw_target = { apdc_cw_register_active_target = yes }
add_to_variable = { apdc_cw_revision = 1 }
apdc_cw_notify_controls = yes
'''
    effects['apdc_cw_lock_law']='apdc_cw_find_law = yes\n'+iff('check_variable = { apdc_cw_law_index > -1 }', 'set_variable = { apdc_cw_law_locked^apdc_cw_law_index = apdc_cw_value }\n'+add('apdc_cw_revision',1)+'apdc_cw_notify_controls = yes')
    effects['apdc_cw_remove_law']='apdc_cw_find_law = yes\n'+iff('check_variable = { apdc_cw_law_index > -1 }','set_variable = { apdc_cw_law_running^apdc_cw_law_index = 0 }\nset_variable = { apdc_cw_law_unlocked^apdc_cw_law_index = 0 }\n'+add('apdc_cw_revision',1)+'apdc_cw_notify_controls = yes')
    effects['apdc_cw_submit_law']='''if = { limit = { apdc_cw_can_select_law = yes }
set_temp_variable = { apdc_cw_payment = apdc_cw_law_execute_cost^apdc_cw_law_row }
multiply_temp_variable = { apdc_cw_payment = -1 }
add_political_power = apdc_cw_payment
set_variable = { apdc_cw_law_running^apdc_cw_law_row = apdc_cw_option }
add_to_variable = { apdc_cw_revision = 1 }
apdc_cw_refresh_view = yes
}'''
    effects['apdc_cw_tick_laws']='''for_each_loop = { array = apdc_cw_law_id index = apdc_cw_tick_record value = apdc_cw_tick_id
set_variable = { apdc_cw_law_last_delta^apdc_cw_tick_record = 0 }
if = { limit = { check_variable = { apdc_cw_law_running^apdc_cw_tick_record = 1 } }
set_variable = { global.apdc_cw_tick_owner = THIS }
set_variable = { global.apdc_cw_tick_target = apdc_cw_law_target^apdc_cw_tick_record }
set_variable = { global.apdc_cw_tick_actor = apdc_cw_law_beneficiary^apdc_cw_tick_record }
if = { limit = { var:global.apdc_cw_tick_target = { exists = yes } var:global.apdc_cw_tick_actor = { exists = yes } exists = yes }
set_variable = { global.apdc_cw_tick_axis = apdc_cw_law_axis^apdc_cw_tick_record }
set_variable = { global.apdc_cw_tick_delta = apdc_cw_law_rate^apdc_cw_tick_record }
set_variable = { apdc_cw_law_last_delta^apdc_cw_tick_record = apdc_cw_law_rate^apdc_cw_tick_record }
var:global.apdc_cw_tick_target = {
set_variable = { apdc_cw_actor = global.apdc_cw_tick_actor }
set_variable = { apdc_cw_axis = global.apdc_cw_tick_axis }
set_variable = { apdc_cw_delta = global.apdc_cw_tick_delta }
apdc_cw_change_control = yes
'''+''.join(iff(f'check_variable = {{ apdc_cw_axis = {i} }}',f'add_to_variable = {{ apdc_cw_law_delta_{a}^apdc_cw_source_index = apdc_cw_delta }}') for i,a in enumerate(AXES,1))+'''
} } else = { set_variable = { apdc_cw_law_running^apdc_cw_tick_record = 0 } }
} }'''
    effects['apdc_cw_political_attraction']='''for_loop_effect = { start = 1 end = apdc_cw_sources^num value = apdc_cw_attraction_index
set_variable = { apdc_cw_actor = apdc_cw_sources^apdc_cw_attraction_index }
if = { limit = { var:apdc_cw_actor = { exists = yes } }
set_temp_variable = { apdc_cw_gap = apdc_cw_economic^apdc_cw_attraction_index }
add_to_temp_variable = { apdc_cw_gap = apdc_cw_military^apdc_cw_attraction_index }
multiply_temp_variable = { apdc_cw_gap = 0.5 }
subtract_from_temp_variable = { apdc_cw_gap = apdc_cw_political^apdc_cw_attraction_index }
if = { limit = { check_variable = { apdc_cw_gap > 0 } }
set_variable = { apdc_cw_delta = apdc_cw_gap }
multiply_variable = { apdc_cw_delta = 0.01 }
clamp_variable = { var = apdc_cw_delta min = 0.01 max = 0.1 }
clamp_variable = { var = apdc_cw_delta max = apdc_cw_gap }
set_variable = { apdc_cw_axis = 1 }
apdc_cw_change_control = yes
add_to_variable = { apdc_cw_auto_delta^apdc_cw_attraction_index = apdc_cw_delta }
} } }'''
    snapshots=''
    for a in AXES:
        snapshots+=f'clear_array = apdc_cw_old_{a}\nclear_array = apdc_cw_law_delta_{a}\nfor_each_loop = {{ array = apdc_cw_{a} add_to_array = {{ array = apdc_cw_old_{a} value = var:v }} add_to_array = {{ array = apdc_cw_law_delta_{a} value = 0 }} }}\n'
    snapshots+='clear_array = apdc_cw_auto_delta\nfor_each_loop = { array = apdc_cw_sources add_to_array = { array = apdc_cw_auto_delta value = 0 } }\n'
    effects['apdc_cw_snapshot']=snapshots
    effects['apdc_cw_daily']='''add_to_variable = { global.apdc_cw_daily_batches = 1 }
set_global_flag = apdc_cw_ticking
for_each_scope_loop = { array = global.apdc_cw_active_targets apdc_cw_snapshot = yes }
for_each_scope_loop = { array = global.apdc_cw_law_owners apdc_cw_tick_laws = yes }
for_each_scope_loop = { array = global.apdc_cw_active_targets
if = { limit = { exists = yes } apdc_cw_political_attraction = yes }
}
clr_global_flag = apdc_cw_ticking
every_country = { limit = { is_ai = no has_country_flag = apdc_cw_open }
apdc_cw_refresh_view = yes }
'''
    effects['apdc_cw_bootstrap']='''if = { limit = { NOT = { has_global_flag = apdc_cw_ready_v1 } }
set_global_flag = apdc_cw_ready_v1
apdc_cw_initialize_geometry = yes
every_country = { apdc_cw_ensure = yes }
GER = {
set_variable = { apdc_cw_target = FRA } set_variable = { apdc_cw_value = 1 } apdc_cw_set_intervention = yes
set_variable = { apdc_cw_target = LLU } apdc_cw_set_intervention = yes
}
'''
    for status,tags in [(6,'USA SOV CHI'),(5,'GER FRA ENG LLU JAP ITA BRA PAK TUR AST CAN'),(3,'AFG YEM HAI SOM SSD CHA CAR NGR MLI BKF')]:
        effects['apdc_cw_bootstrap']+=''.join(f'{tag} = {{ set_variable = {{ apdc_cw_status = {status} }} }}\n' for tag in tags.split())
    effects['apdc_cw_bootstrap']+='apdc_cw_register_test_laws = yes\n}\n'
    effects['apdc_cw_open_panel']='''apdc_cw_bootstrap = yes
if = { limit = { has_country_flag = apdc_cw_open } clr_country_flag = apdc_cw_open }
else = {
set_country_flag = apdc_cw_open
set_variable = { apdc_cw_selected = THIS }
set_variable = { apdc_cw_tab = 1 }
set_variable = { apdc_cw_detail = 0 }
apdc_cw_bind_world_ui = yes
apdc_cw_refresh_view = yes
}'''
    write('common/scripted_effects/APDC_cold_war.txt',''.join(block(k,v) for k,v in effects.items()))
    write('common/on_actions/APDC_cold_war.txt','''on_actions = {
on_startup = { effect = { GER = { apdc_cw_bootstrap = yes } every_country = { limit = { is_ai = no } apdc_cw_bind_world_ui = yes } } }
on_daily = { effect = { if = { limit = { NOT = { has_global_flag = apdc_cw_daily_lock } } set_global_flag = { flag = apdc_cw_daily_lock value = 1 days = 1 } apdc_cw_bootstrap = yes apdc_cw_daily = yes } } }
on_state_owner_changed = { effect = { if = { limit = { has_global_flag = apdc_cw_ready_v1 } apdc_cw_invalidate_maps = yes } } }
}''')
    write('common/scripted_triggers/APDC_cold_war.txt','''apdc_cw_can_select_law = {
check_variable = { apdc_cw_law_locked^apdc_cw_law_row = 0 }
check_variable = { apdc_cw_law_unlocked^apdc_cw_law_row = 1 }
NOT = { check_variable = { apdc_cw_law_running^apdc_cw_law_row = apdc_cw_option } }
OR = { check_variable = { apdc_cw_option = 0 } check_variable = { apdc_cw_option = 1 } }
NOT = { check_variable = { political_power < apdc_cw_law_execute_cost^apdc_cw_law_row } }
}''')

if __name__=='__main__': build()
