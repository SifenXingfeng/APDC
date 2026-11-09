"""Six shared law groups, native/custom effects and special-bill registration."""
import re
from common import *

NATIVE={
 '建设速度':'production_speed_buildings_factor','建造速度':'production_speed_buildings_factor',
 '科研速度':'research_speed_factor','战略资源获取效率':'local_resources_factor',
 '工厂产出':'industrial_capacity_factory','海军船坞产出':'industrial_capacity_dockyard',
 '稳定度':'stability_factor','战争支持度':'war_support_factor',
 '人力可用比例':'conscription_factor','每月人口':'monthly_population','月度人口':'monthly_population',
 '每日政治点数':'political_power_gain','专项计划速度':'special_project_speed_factor',
 '每周稳定度':'stability_weekly'
}
CUSTOM={
 '建造维护费':'APDC_eco_construction_maintenance_factor',
 '军工生产维护费':'APDC_eco_mil_maintenance_factor','船坞生产维护费':'APDC_eco_nav_maintenance_factor',
 '生活消费品人口系数':'APDC_eco_population_factor','消费品系数':'APDC_eco_population_factor',
 '私营民工扩张速度':'APDC_eco_private_civ_expansion_factor','私营军工扩张速度':'APDC_eco_private_mil_expansion_factor',
 '私营企业收购价格':'APDC_eco_private_acquisition_factor','私营军工装备购买费用':'APDC_eco_private_equipment_purchase_factor',
 '每周社会发展等级增长':'APDC_eco_society_weekly','每周科研发展等级增长':'APDC_eco_science_weekly',
 '人形科技科研速度':P+'doll_research_factor','遗迹专项计划速度':P+'relic_project_factor',
 '每月人力':P+'monthly_manpower_factor','每周人力':P+'weekly_manpower_factor'
}


def modifiers(option, manpower_mode):
    result={}
    for line in option['effects']:
        if line.startswith(('×','√')) or '：' not in line:continue
        key,value=line.split('：',1)
        if key=='议会名称':continue
        if key in ('议案审议时间','党派提供加成','党派反对权'):continue
        if key=='每月人力' and manpower_mode['monthly']=='population':field='monthly_population'
        elif key=='每周人力' and manpower_mode['weekly']=='population':field='monthly_population'
        else:field=NATIVE.get(key,CUSTOM.get(key))
        if field is None:raise ValueError('Unmapped law effect: '+line)
        numeric=float(value.rstrip('%'))/(100 if value.endswith('%') else 1)
        result[field]=result.get(field,0)+numeric
    return result


def generate(loc):
    groups=load_json('laws.json')['groups']
    regimes=load_json('regimes.json')
    settings=load_json('settings.json')
    eco=json.loads(read('docs/parliament/20261107-design/opening_policy.json'))['economic_names']
    mode=settings['manpower_mode']
    effects='';ideas='';extra_defs=''
    for key in [P+'doll_research_factor',P+'relic_project_factor',P+'monthly_manpower_factor',P+'weekly_manpower_factor','APDC_eco_private_acquisition_factor','APDC_eco_private_equipment_purchase_factor']:
        extra_defs+=block(key,'color_type = '+('bad' if 'acquisition' in key or 'purchase' in key else 'good')+'\nvalue_type = percentage\nprecision = 2\ncategory = country')
    write('common/modifier_definitions/apdc_parliament_law_modifiers.txt',extra_defs)
    for g in groups:
        loc[P+'group_'+str(g['id'])]=g['name']
        for o in g['options']:
            key=P+'law_'+g['key']+'_'+str(o['id'])
            loc[key]=o['name']
            colored=[]
            for line in o['effects']:
                if line.startswith(('×','√')):
                    colored.append(('§R' if line.startswith('×') else '§G')+line+'§!')
                elif '：' in line:
                    name,value=line.split('：',1)
                    if re.fullmatch(r'[+\-]?\d+(?:\.\d+)?%?',value):
                        bad=any(v in name for v in ['维护费','购买费用','收购价格','消费品人口系数','消费品系数'])
                        n=float(value.rstrip('%'));color='Y' if n==0 else 'G' if (n<0)==bad else 'R'
                        colored.append(name+'：§'+color+value+'§!')
                    else:colored.append(line)
                else:colored.append(line)
            loc[key+'_desc']='\n'.join(colored)
            loc[key+'_tip']='§Y'+o['name']+'§!\n\n$'+key+'_desc$'
            body=''
            if g['id']<=4:
                body+=''.join('remove_ideas = '+P+'law_'+g['key']+'_'+str(v['id'])+'\n' for v in g['options'])
                body+='add_ideas = '+key+'\n'
                mod=modifiers(o,mode)
                idea='allowed = { always = no }\nallowed_civil_war = { always = yes }\nremoval_cost = -1\n'+block('modifier','\n'.join(k+' = '+str(v) for k,v in mod.items()))
                ideas+=block(key,idea)
                body+=('set_country_flag = '+P+'relic_research_forbidden\n') if '×可以进行遗迹技术研究' in o['effects'] else ('clr_country_flag = '+P+'relic_research_forbidden\n' if g['key']=='relic_technology' else '')
            elif g['id']==5:
                economic=next(k for k,v in eco.items() if v==o['name'])
                body+='APDC_set_economic_system_'+economic+' = yes\n'
            elif g['id']==6:
                body+=sv('regime',o['id'])+'apdc_parl_refresh_regime = yes\n'
            body+=sv('law_'+str(g['id']),o['id'])+'force_update_dynamic_modifier = yes\n'+op('dirty','add',1)
            effects+=effect('enact_'+g['key']+'_'+str(o['id']),body)
            submit=iff(P+'can_submit = yes NOT = { '+ck('law_'+str(g['id']),'=',o['id'])+' } has_political_power > '+str(settings['proposal_cost']-1),
                       'add_political_power = -'+str(settings['proposal_cost'])+'\n'+P+'submit_agenda = { KIND = 1 TARGET = '+str(g['id'])+' OPTION = '+str(o['id'])+' }\n')
            effects+=effect('propose_'+g['key']+'_'+str(o['id']),submit)
    write('common/ideas/apdc_parliament_laws.txt',block('ideas',block('hidden_ideas',ideas)))
    # Story-owned special bill IDs and callbacks; no fixed country/finite GUI.
    register='add_to_array = { '+P+'special_ids = $ID$ }\nadd_to_array = { '+P+'special_names = token:$NAME$ }\nadd_to_array = { '+P+'special_descriptions = token:$DESC$ }\nadd_to_array = { '+P+'special_costs = $COST$ }\nadd_to_array = { '+P+'special_enabled = 1 }\n'+op('dirty','add',1)
    effects+=effect('register_special_bill',iff('NOT = { is_in_array = { array = '+P+'special_ids value = $ID$ } }',register))
    effects+=effect('remove_special_bill',sv('special_remove_id','$ID$')+sv('special_scan',0)+block('while_loop_effect','limit = { '+ck('special_scan','<',P+'special_ids^num')+' }\n'+iff(ck('special_remove_id','=',P+'special_ids^'+var('special_scan')),
        'remove_from_array = { array = '+P+'special_ids index = '+var('special_scan')+' }\nremove_from_array = { array = '+P+'special_names index = '+var('special_scan')+' }\nremove_from_array = { array = '+P+'special_descriptions index = '+var('special_scan')+' }\nremove_from_array = { array = '+P+'special_costs index = '+var('special_scan')+' }\nremove_from_array = { array = '+P+'special_enabled index = '+var('special_scan')+' }\n',op('special_scan','add',1)))+op('dirty','add',1))
    effects+=effect('set_special_bill_availability',sv('special_scan',0)+block('while_loop_effect','limit = { '+ck('special_scan','<',P+'special_ids^num')+' }\n'+iff('check_variable = { '+P+'special_ids^'+var('special_scan')+' = $ID$ }','set_variable = { '+P+'special_enabled^'+var('special_scan')+' = $AVAILABLE$ }\n')+op('special_scan','add',1))+op('dirty','add',1))
    effects+=effect('submit_special_bill',iff(P+'can_submit = yes '+ck('selected_special_index','>=',0)+' '+ck('selected_special_index','<',P+'special_ids^num')+' check_variable = { '+P+'special_enabled^'+var('selected_special_index')+' = 1 }',
        sv('special_cost',P+'special_costs^'+var('selected_special_index'))+iff('NOT = { has_political_power < '+var('special_cost')+' }',
            sv('special_payment',var('special_cost'))+op('special_payment','multiply',-1)+'add_political_power = '+var('special_payment')+'\n'+
            sv('agenda',1)+sv('stage',1)+sv('progress',0)+sv('bill_work',0)+sv('bill_base_days',var('base_days'))+sv('bill_kind',4)+sv('bill_target',P+'special_ids^'+var('selected_special_index'))+
            'set_variable = { '+P+'special_active_name = '+P+'special_names^'+var('selected_special_index')+' }\napdc_parl_special_submitted_dispatch = yes\napdc_parl_special_submitted_hook = yes\napdc_parl_refresh = yes\n'+iff(ck('base_days','=',0),sv('progress',100)+'apdc_parl_validate_agenda = yes\n'))))
    effects+=effect('execute_special_bill',sv('last_passed_special_id',var('bill_target'))+'apdc_parl_special_passed_dispatch = yes\napdc_parl_special_passed_hook = yes\n')
    write('common/scripted_effects/apdc_parliament_laws.txt',effects)
    hooks='common/scripted_effects/apdc_parliament_story_hooks.txt'
    hook_text=read(hooks) if (ROOT/hooks).exists() else '# Story-owned extension. Never regenerated over authored content.\n'
    for name in ['special_passed_hook','special_failed_hook','special_submitted_hook']:
        if not any(n.key==P+name for n in parse(hook_text)):hook_text+=effect(name,'# Dispatch by the active/last special bill ID here.')
    write(hooks,hook_text)
    write('common/scripted_triggers/apdc_parliament_research_hooks.txt',block(P+'can_research_relic','NOT = { has_country_flag = '+P+'relic_research_forbidden }'))
    # User-selected periodic manpower semantics are kept explicit in settings.
    periodic=''
    if mode['weekly']=='pool':
        periodic+=effect('weekly_manpower',sv('manpower_delta','manpower')+op('manpower_delta','multiply','modifier@'+P+'weekly_manpower_factor')+'add_manpower = '+var('manpower_delta')+'\n')
    if mode['monthly']=='pool':
        periodic+=effect('monthly_manpower',sv('manpower_delta','manpower')+op('manpower_delta','multiply','modifier@'+P+'monthly_manpower_factor')+'add_manpower = '+var('manpower_delta')+'\n')
    write('common/scripted_effects/apdc_parliament_periodic_laws.txt',periodic or '# Population-growth semantics use native monthly_population.\n')
    on=''
    if mode['weekly']=='pool':on+='on_weekly = { effect = { if = { limit = { NOT = { has_global_flag = apdc_parl_weekly_lock } } set_global_flag = { flag = apdc_parl_weekly_lock days = 7 value = 1 } every_country = { apdc_parl_weekly_manpower = yes } } } }\n'
    if mode['monthly']=='pool':on+='on_monthly = { effect = { if = { limit = { NOT = { has_global_flag = apdc_parl_monthly_lock } } set_global_flag = { flag = apdc_parl_monthly_lock days = 27 value = 1 } every_country = { apdc_parl_monthly_manpower = yes } } } }\n'
    write('common/on_actions/zzzz_apdc_parliament_periodic_laws.txt',block('on_actions',on))
