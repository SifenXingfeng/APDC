"""Update the one shared economic-system state and the real economy pathways."""
from common import *
from laws import modifiers
import re


def replace_effect(text, key, body):
    node=next(n for n in parse(text) if n.key==key)
    return text[:node.start]+block(key,body)+text[node.end:]


def generate(loc):
    policy=json.loads(read('docs/parliament/20261107-design/opening_policy.json'))
    eco=policy['economic_names']
    group=next(g for g in load_json('laws.json')['groups'] if g['id']==5)
    mode=load_json('settings.json')['manpower_mode']
    ideas=''
    for key,name in eco.items():
        option=next(o for o in group['options'] if o['name']==name)
        body='allowed = { always = no }\nallowed_civil_war = { always = yes }\nremoval_cost = -1\n'
        body+=block('modifier','\n'.join(k+' = '+str(v) for k,v in modifiers(option,mode).items()))
        ideas+=block('APDC_economic_system_'+key+'_idea',body)
        # Keep the existing tooltip/name keys and replace their definitions in
        # the existing source file, avoiding localization-order collisions.
    write('common/ideas/APDC_economic_systems.txt',block('ideas',block('hidden_ideas',ideas)))
    old_loc=read('localisation/simp_chinese/APDC_economic_systems_l_simp_chinese.yml')
    entries={}
    for line in old_loc.splitlines():
        m=re.match(r'\s*([A-Za-z0-9_]+):(?:\d+)?\s+"(.*)"',line)
        if m:entries[m[1]]=m[2]
    for key,name in eco.items():
        option=next(o for o in group['options'] if o['name']==name)
        entries['APDC_economic_system_'+key+'_idea']=name
        entries['APDC_economic_system_'+key+'_idea_desc']='§Y'+name+'§!\\n\\n'+loc[P+'law_economic_system_'+str(option['id'])+'_desc'].replace('\n','\\n')
    lines=['l_simp_chinese:']+[' '+k+':0 "'+v.replace('"','\\"')+'"' for k,v in entries.items()]
    write('localisation/simp_chinese/APDC_economic_systems_l_simp_chinese.yml','\n'.join(lines)+'\n',True)
    fx=read('common/scripted_effects/APDC_economic_system_scripted_effects.txt')
    clear='remove_ideas = { '+' '.join('APDC_economic_system_'+key+'_idea' for key in eco)+' }\n'
    fx=replace_effect(fx,'APDC_clear_economic_system',clear)
    for i,(key,name) in enumerate(eco.items(),1):
        option=next(o for o in group['options'] if o['name']==name)
        body='APDC_clear_economic_system = yes\nadd_ideas = APDC_economic_system_'+key+'_idea\n'+sv('law_5',i)
        body+='clr_country_flag = APDC_eco_private_acquisition_forbidden\nclr_country_flag = APDC_eco_private_plunder_allowed\n'
        if '×可以收购私营企业' in option['effects']:body+='set_country_flag = APDC_eco_private_acquisition_forbidden\n'
        if '√可以掠夺私营企业' in option['effects']:body+='set_country_flag = APDC_eco_private_plunder_allowed\n'
        body+='if = { limit = { has_country_flag = APDC_eco_initialized } APDC_eco_reconcile_planned = yes APDC_eco_refresh_policies = yes APDC_eco_refresh_current_supply = yes APDC_eco_calculate_budget = yes }\n'+op('dirty','add',1)
        fn='APDC_set_economic_system_'+key
        if any(n.key==fn for n in parse(fx)):fx=replace_effect(fx,fn,body)
        else:fx+=block(fn,body)
    write('common/scripted_effects/APDC_economic_system_scripted_effects.txt',fx)
    triggers=read('common/scripted_triggers/APDC_economic_system_scripted_triggers.txt')
    node=next(n for n in parse(triggers) if n.key=='APDC_has_economic_system')
    triggers=triggers[:node.start]+block('APDC_has_economic_system','OR = { '+' '.join('has_idea = APDC_economic_system_'+key+'_idea' for key in eco)+' }')+triggers[node.end:]
    write('common/scripted_triggers/APDC_economic_system_scripted_triggers.txt',triggers)
    # Preserve distribution-policy classification. Split only private-industry
    # prohibition/nationalization, so decentralized planning retains firms.
    ep='tools/economy/build_backend.py'
    source=read(ep)
    old="triggers=block(P+'is_planned','OR = { has_idea = APDC_economic_system_decentralized_planning_idea has_idea = APDC_economic_system_central_planning_idea }')"
    extra="\n triggers+=block(P+'disallows_private','has_idea = APDC_economic_system_central_planning_idea')"
    if extra.strip() not in source:
        assert old in source
        source=source.replace(old,old+extra)
    source=source.replace("c+=cond(P+'is_planned = yes',setv(kind+'_capacity',0)+setv(kind+'_velocity',0))","c+=cond(P+'disallows_private = yes',setv(kind+'_capacity',0)+setv(kind+'_velocity',0))")
    start=source.index('def build_planned():');end=source.index('\ndef build_budget():',start)
    new="""def build_planned():
 b='APDC_eco_initialize_stock_arrays = yes\\n'
 b+=cond(P+'is_planned = yes',
  cond('NOT = { has_idea = APDC_eco_distribution_5 }',
   ''.join('remove_ideas = APDC_eco_distribution_'+str(i)+'\\n' for i in range(1,5))+'add_ideas = APDC_eco_distribution_5\\n'),
  cond('has_idea = APDC_eco_distribution_5','remove_ideas = APDC_eco_distribution_5\\nadd_ideas = APDC_eco_distribution_1\\n'))
 conversion='every_controlled_state = {\\n'+''.join(
   f'set_temp_variable = {{ APDC_eco_convert = building_level@APDC_eco_private_{k} }}\\n'
   f'if = {{ limit = {{ check_variable = {{ APDC_eco_convert > 0 }} }} set_building_level = {{ type = APDC_eco_private_{k} level = 0 }} '
   f'add_building_construction = {{ type = {native} level = APDC_eco_convert instant_build = yes }} }}\\n'
   for k,native in [('civ','industrial_complex'),('mil','arms_factory')])+'}\\nAPDC_eco_nationalize_stock = yes\\nclr_country_flag = APDC_eco_statistics_today\\nset_country_flag = APDC_eco_planned_normalized\\n'+setv('civ_progress',0)+setv('mil_progress',0)
 b+=cond(P+'disallows_private = yes',cond('OR = { NOT = { has_country_flag = APDC_eco_planned_normalized } has_country_flag = APDC_eco_private_stock_dirty '+check('private_civ_raw','>',0)+' '+check('private_mil_raw','>',0)+' }',conversion),'clr_country_flag = APDC_eco_planned_normalized\\n')
 return effect('reconcile_planned',b)

"""
    source=source[:start]+new+source[end:]
    write(ep,source)
    # Build only the affected effects from the maintained generator; never run
    # migration, technology-hook rewrites, market generation or a full build.
    import importlib.util
    econ_path=ROOT/'tools/economy'
    previous_common=sys.modules.get('common')
    spec=importlib.util.spec_from_file_location('apdc_economy_helpers',econ_path/'common.py')
    helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    sys.modules['common']=helpers
    sys.path.insert(0,str(econ_path))
    try:
        spec=importlib.util.spec_from_file_location('apdc_economy_backend_generator',econ_path/'build_backend.py')
        gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
        generated=helpers.lower_math(gen.build_growth()+gen.build_planned())
    finally:
        sys.path.remove(str(econ_path));sys.modules['common']=previous_common
    runtime=read('common/scripted_effects/APDC_economy_backend.txt')
    for node in parse(generated):
        text=generated[node.start:node.end]
        old_node=next(n for n in parse(runtime) if n.key==node.key)
        runtime=runtime[:old_node.start]+text+runtime[old_node.end:]
    write('common/scripted_effects/APDC_economy_backend.txt',runtime)
    tr=read('common/scripted_triggers/APDC_economy_triggers.txt')
    if 'APDC_eco_disallows_private' not in tr:tr+='\n'+block('APDC_eco_disallows_private','has_idea = APDC_economic_system_central_planning_idea')
    tr+='\n' if not tr.endswith('\n') else ''
    for key,body in [('APDC_eco_can_acquire_private','NOT = { has_country_flag = APDC_eco_private_acquisition_forbidden }'),('APDC_eco_can_plunder_private','has_country_flag = APDC_eco_private_plunder_allowed')]:
        if key not in tr:tr+=block(key,body)
    write('common/scripted_triggers/APDC_economy_triggers.txt',tr)
    # One price function feeds popup totals and actual payment. Production IC
    # and stored equipment cost arrays keep their existing values.
    factor='set_temp_variable = { APDC_eco_purchase_price_factor = modifier@APDC_eco_private_equipment_purchase_factor }\nadd_to_temp_variable = { APDC_eco_purchase_price_factor = 1 }\nclamp_temp_variable = { var = APDC_eco_purchase_price_factor min = 0 }\nmultiply_variable = { APDC_eco_purchase_unit_k = APDC_eco_purchase_price_factor }\n'
    runtime=read('common/scripted_effects/APDC_economy_equipment.txt')
    if 'APDC_eco_purchase_price_factor' not in runtime:
        marker='clamp_variable = { var = APDC_eco_purchase_quantity min = 0 max = APDC_eco_purchase_stock }'
        assert marker in runtime
        runtime=runtime.replace(marker,factor+marker)
    write('common/scripted_effects/APDC_economy_equipment.txt',runtime)
    source=read('tools/economy/build_equipment.py')
    if 'APDC_eco_purchase_price_factor' not in source:
        marker="s+=effect('prepare_purchase','APDC_eco_ensure_equipment = yes\\n'+prepare+"
        assert marker in source
        source=source.replace(marker,"price_factor="+repr(factor)+"\n "+marker+"price_factor+")
    write('tools/economy/build_equipment.py',source)
    gfx='';ui='';props='';events='';visibility=''
    for key,name in eco.items():
        img=Path('D:/Desktop/经济体制')/(name+'.png')
        write('gfx/interface/APDC/economic_systems/'+key+'.png',img.read_bytes())
        gfx+=block('spriteType','name = "GFX_APDC_economic_system_'+key+'"\ntexturefile = "gfx/interface/APDC/economic_systems/'+key+'.png"')
        ui+=block('buttonType','name = "APDC_economic_system_'+key+'"\nposition = { x = 26 y = 654 }\nquadTextureSprite = "GFX_APDC_economic_system_'+key+'"\nclicksound = click_default\npdx_tooltip = "APDC_economic_system_'+key+'_idea_desc"')
        events+='APDC_economic_system_'+key+'_click = { clear_variable = APDC_eco_selected_group clear_variable = APDC_eco_purchase_open clear_variable = APDC_eco_trade_open set_variable = { APDC_eco_panel_open = 1 } clr_country_flag = APDC_eco_research_counted_today APDC_eco_refresh_current_supply = yes APDC_eco_calculate_budget = yes APDC_eco_sync_ui = yes }\n'
        visibility+='APDC_economic_system_'+key+'_visible = { has_idea = APDC_economic_system_'+key+'_idea }\n'
    # Preserve the original entry coordinates instead of guessing a new slot.
    old_ui=read('interface/APDC_economic_system.gui')
    pos=re.search(r'position\s*=\s*\{\s*x\s*=\s*([-\d]+)\s+y\s*=\s*([-\d]+)',old_ui)
    old_nodes=parse(old_ui);window=next(n for n in old_nodes if n.key=='guiTypes').children[0]
    button=next(n for n in window.children if n.key=='buttonType')
    position=button.get('position')
    if position:ui=re.sub(r'position = \{ x = 26 y = 654 \}',old_ui[position.start:position.end],ui)
    # Keep outer container attributes and only replace its button entries.
    kept='\n'.join(old_ui[n.start:n.end] for n in window.children if n.key!='buttonType')
    write('interface/APDC_economic_system.gui',block('guiTypes',block('containerWindowType',kept+'\n'+ui)))
    write('interface/APDC_economic_system.gfx',block('spriteTypes',gfx))
    write('common/scripted_guis/APDC_economic_system_scripted_gui.txt',block('scripted_gui',block('APDC_economic_system_ui','context_type = player_context\nwindow_name = "APDC_economic_system_window"\nparent_window_name = "APDC_economic_system_hook"\nvisible = { always = yes }\n'+block('effects',events)+block('triggers',visibility))))
