"""Cold War panel, alpha-tested world-map targets and dynamic control tabs."""
import json,math
from common import ROOT, block, iff, setv, add, write, metadata
from build_backend import AXES

def build():
    g=metadata();ui=[];sg=[];local=json.loads((ROOT/'docs/cold-war/20261024/view-localisation.json').read_text('utf-8'));defined=[]
    local.update({'APDC_CW_TITLE':'冷战','APDC_CW_BACK':'返回','APDC_CW_EMPTY':'','APDC_CW_NONE':'无','APDC_CW_AUTONOMY':'自主','APDC_CW_POLITICAL':'政治控制','APDC_CW_ECONOMIC':'经济控制','APDC_CW_MILITARY':'军事控制','APDC_CW_EXECUTE':'执行','APDC_CW_STOP':'停止','APDC_CW_NO_LAWS':'暂无已解锁法案','APDC_CW_LEGEND':'[APDCCWLegendName]','APDC_CW_COUNTRY':'[?apdc_cw_selected.GetNameDef]','APDC_CW_IDEOLOGY':'意识形态：[?apdc_cw_selected.GetRulingIdeology]','APDC_CW_ECONOMY':'经济体制：[APDCCWEconomy]','APDC_CW_FACTION':'军事阵营：[APDCCWFaction]','APDC_CW_ORGANIZATION':'合作组织：[APDCCWOrganization]','APDC_CW_STATUS':'国际地位：[APDCCWStatus]','APDC_CW_P_LEAN':'政治：[APDCCWPoliticalLean]','APDC_CW_E_LEAN':'经济：[APDCCWEconomicLean]','APDC_CW_M_LEAN':'军事：[APDCCWMilitaryLean]','APDC_CW_LEGEND_TIP':'§Y[APDCCWLegendName]§!\n§W[?apdc_cw_ui_shares^apdc_cw_legend_id|2]%§!','APDC_CW_LAW_NAME':'[APDCCWLawName]','APDC_CW_LAW_EXECUTE_COST':'[APDCCWExecuteCost]','APDC_CW_LAW_STOP_COST':'[APDCCWStopCost]','APDC_CW_LAW_TIP':'§Y[APDCCWLawName]§!\n\n[APDCCWLawDescription]','APDC_CW_LEGEND_SELF':'自主','APDC_CW_LEGEND_COUNTRY':'[?apdc_cw_ui_sources^apdc_cw_legend_id.GetName]','APDC_CW_FACTION_NAME':'[?apdc_cw_selected.GetFactionName]','APDC_CW_EXECUTE_COST_Y':'§Y£pol_power [?apdc_cw_law_execute_cost^apdc_cw_law_row|0]§!','APDC_CW_EXECUTE_COST_R':'§R£pol_power [?apdc_cw_law_execute_cost^apdc_cw_law_row|0]§!','APDC_CW_STOP_COST_Y':'§Y£pol_power [?apdc_cw_law_stop_cost^apdc_cw_law_row|0]§!','APDC_CW_STOP_COST_R':'§R£pol_power [?apdc_cw_law_stop_cost^apdc_cw_law_row|0]§!'})
    def dt(name,clauses):defined.append(block('defined_text','name = '+name+'\n'+''.join('text = { '+('trigger = { '+test+' } ' if test else '')+'localization_key = '+key+' }\n' for test,key in clauses)))
    def icon(name,x,y,sprite,other=''):
        return block('iconType',f'name = "{name}" position = {{ x = {x} y = {y} }} spriteType = "{sprite}" '+other)
    def text(name,x,y,key,width,height=30,font='hoi_20b',extra=''):
        return block('instantTextboxType',f'name = "{name}" position = {{ x = {x} y = {y} }} font = "{font}" text = "{key}" maxWidth = {width} maxHeight = {height} fixedsize = yes truncate = no vertical_alignment = center alwaystransparent = yes '+extra)
    def button(name,x,y,sprite='GFX_APDC_cw_hit',size=None,tip=None,extra=''):
        if sprite=='GFX_APDC_cw_hit':
            assert size, 'Input textures require the real button dimensions'
            sprite=f'GFX_APDC_cw_hit_{size[0]}_{size[1]}'
        return block('buttonType',f'name = "{name}" position = {{ x = {x} y = {y} }} spriteType = "{sprite}" '+(f'size = {{ x = {size[0]} y = {size[1]} }} ' if size else '')+(f'pdx_tooltip = "{tip}" ' if tip else '')+'clicksound = click_default '+extra)
    def scripted(name,window,visible,props='',triggers='',effects='',lists='',parent='',dirty=''):
        sg.append(block(name,'context_type = player_context\nwindow_name = "'+window+'"\nvisible = { '+visible+' }\n'+('parent_scripted_gui = '+parent+'\n' if parent else '')+('dirty = '+dirty+'\n' if dirty else '')+block('properties',props)+block('triggers',triggers)+block('effects',effects)+block('dynamic_lists',lists)))
    # The 93x92 native hit texture pads the original 83x80 art by (5,6).
    ui.append(block('containerWindowType','name = "apdc_cw_entry" position = { x = 0 y = 0 } size = { width = 93 height = 92 } clipping = no\n'+button('apdc_cw_entry_button',0,0,'GFX_APDC_cw_politics_entry',tip='APDC_CW_TITLE')))
    sg.append(block('apdc_cw_entry','context_type = player_context\nparent_window_name = "APDC_cold_war_entry_hook"\nwindow_name = "apdc_cw_entry"\nvisible = { always = yes }\n'+block('effects','apdc_cw_entry_button_click = { apdc_cw_open_panel = yes }')))
    # Native window background provides dragging, following the cabinet panel.
    root=block('background','name = "apdc_cw_background" spriteType = "GFX_APDC_cw_background"')+button('apdc_cw_close',12,11,'GFX_APDC_custom_panel_exit',size=(96,47),tip='CLOSE')
    ui.append(block('containerWindowType','name = "apdc_cw_panel" orientation = center origo = center position = { x = 0 y = 10 } size = { width = 1078 height = 972 } moveable = yes click_to_front = yes clipping = no\n'+root))
    scripted('apdc_cw_panel','apdc_cw_panel','has_country_flag = apdc_cw_open',effects='apdc_cw_close_click = { clr_country_flag = apdc_cw_open }')
    from world_renderer import fast_mode,build_fast_ui
    if fast_mode():
        build_fast_ui(g,ui,local,scripted,button,icon)
    else:
        # Preserve native geometry and cache ownership checks on map changes.
        # Rebuilding native lists moved work into first opening/territory changes.
        world='';props='';triggers='';effects='';done=set()
        for entry in g['pieces']:
            w=entry['world'];sid=entry['state'];name=f'apdc_cw_world_{entry["id"]}'
            world+=button(name,w['x'],w['y'],w['image'],tip=f'APDC_CW_STATE_{sid}')
            world+=icon(name+'_fill',w['x'],w['y'],w['image'],'alwaystransparent = yes')
            props+=block(name+'_fill',f'image = "[?apdc_cw_world_fill_images^{entry["id"]}.GetTokenKey]" frame = apdc_cw_world_fill_frames^{entry["id"]}')
            triggers+=block(name+'_click_enabled',f'OR = {{ check_variable = {{ apdc_cw_world_frames^{sid} = 3 }} check_variable = {{ apdc_cw_world_frames^{sid} = 4 }} }}')
            effects+=block(name+'_click',setv('apdc_cw_world_piece_id',entry['id'])+'apdc_cw_select_world_piece = yes')
            if sid not in done:local[f'APDC_CW_STATE_{sid}']=f'§Y[{sid}.Owner.GetName]§!';done.add(sid)
        for entry in g['borders']:
            w=entry['world'];name=f'apdc_cw_border_{entry["id"]}'
            world+=icon(name,w['x'],w['y'],w['image'],'alwaystransparent = yes')
            props+=block(name,f'frame = apdc_cw_world_border_frames^{entry["id"]}')
            triggers+=block(name+'_visible',f'check_variable = {{ apdc_cw_world_border_visible^{entry["id"]} = 1 }}')
        lists=''
        world+=icon('apdc_cw_coasts',0,0,'GFX_APDC_cw_coasts','alwaystransparent = yes')
        world+=icon('apdc_cw_screen_texture',0,0,'GFX_APDC_cw_screen_overlay','alwaystransparent = yes')
        ui.append(block('containerWindowType','name = "apdc_cw_world" position = { x = 38 y = 85 } size = { width = 1000 height = 500 } clipping = yes\n'+world))
        scripted('apdc_cw_world','apdc_cw_world','check_variable = { apdc_cw_detail = 0 }',props,triggers,effects,lists=lists,parent='apdc_cw_panel',dirty='apdc_cw_map_ui_revision')
    # Dynamic detail masks are limited to currently owned states and external borders.
    for kind in ['piece','border']:
        name='apdc_cw_detail_'+kind
        ui.append(block('containerWindowType',f'name = "{name}_entry" size = {{ width = 0 height = 0 }} clipping = no\n'+icon(name,0,0,'GFX_APDC_cw_empty','alwaystransparent = yes')))
    detail=button('apdc_cw_return',12,7,'GFX_APDC_cw_return',extra='buttonText = "APDC_CW_BACK" buttonFont = "hoi_18mbs"')
    local['APDC_CW_NO_CORE_TERRITORY']='暂无拥有的核心领土'
    detail+=text('apdc_cw_no_core',25,235,'APDC_CW_NO_CORE_TERRITORY',450,36,'hoi_20b',extra='format = center')
    info=''
    for idx,key in enumerate(['COUNTRY','IDEOLOGY','ECONOMY','FACTION','ORGANIZATION','STATUS','P_LEAN','E_LEAN','M_LEAN']):
        info+=text('apdc_cw_info_'+key,535,9+idx*47,'APDC_CW_'+key,450,43,'hoi_24header' if idx==0 else 'hoi_20b')
    ui.append(block('containerWindowType','name = "apdc_cw_detail" position = { x = 38 y = 85 } size = { width = 1000 height = 500 } clipping = yes\n'+detail))
    scripted('apdc_cw_detail','apdc_cw_detail','check_variable = { apdc_cw_detail = 1 }',triggers='apdc_cw_no_core_visible = { check_variable = { apdc_cw_detail_state_count = 0 } }',effects='apdc_cw_return_click = { set_variable = { apdc_cw_detail = 0 } set_variable = { apdc_cw_selected = THIS } apdc_cw_bind_world_ui = yes apdc_cw_refresh_view = yes }',parent='apdc_cw_panel',dirty='apdc_cw_detail_ui_revision')
    ui.append(block('containerWindowType','name = "apdc_cw_country_info" position = { x = 38 y = 85 } size = { width = 1000 height = 500 } clipping = yes\n'+info))
    scripted('apdc_cw_country_info','apdc_cw_country_info','check_variable = { apdc_cw_detail = 1 }',parent='apdc_cw_panel',dirty='apdc_cw_control_ui_revision')
    for z,scale in enumerate(g['scales']):
        grids=''.join(block('gridBoxType',f'name = "apdc_cw_detail_{kind}_list_{z}" position = {{ x = 0 y = 0 }} size = {{ width = 5120 height = 2560 }} slotsize = {{ width = 0 height = 0 }} max_slots_horizontal = 1 add_horizontal = no format = "UPPER_LEFT"') for kind in ['piece','border'])
        trans=block('containerWindowType',f'name = "apdc_cw_transform_{z}" position = {{ x = 0 y = 0 }} size = {{ width = 5120 height = 2560 }} scale = {scale:.10f} clipping = no\n'+grids)
        translation=block('containerWindowType',f'name = "apdc_cw_translate_{z}" position = {{ x = 0 y = 0 }} size = {{ width = 0 height = 0 }} clipping = no\n'+trans)
        ui.append(block('containerWindowType',f'name = "apdc_cw_zoom_{z}" position = {{ x = 0 y = 0 }} size = {{ width = 500 height = 500 }} clipping = yes\n'+translation))
        zp=f'apdc_cw_detail_piece = {{ image = "[?global.apdc_cw_piece_images^apdc_cw_detail_piece_id.GetTokenKey]" frame = apdc_cw_detail_frame x = apdc_cw_pieces_x^apdc_cw_detail_piece_id y = apdc_cw_pieces_y^apdc_cw_detail_piece_id }}\napdc_cw_detail_border = {{ image = "[?global.apdc_cw_border_images^apdc_cw_detail_border_id.GetTokenKey]" frame = apdc_cw_border_frame x = apdc_cw_borders_x^apdc_cw_detail_border_id y = apdc_cw_borders_y^apdc_cw_detail_border_id }}'
        zl=f'apdc_cw_detail_piece_list_{z} = {{ array = apdc_cw_detail_pieces value = apdc_cw_detail_piece_id entry_container = "apdc_cw_detail_piece_entry" }}\napdc_cw_detail_border_list_{z} = {{ array = apdc_cw_detail_borders value = apdc_cw_detail_border_id entry_container = "apdc_cw_detail_border_entry" }}'
        scripted('apdc_cw_zoom_'+str(z),'apdc_cw_zoom_'+str(z),f'check_variable = {{ apdc_cw_detail_zoom = {z} }}',props=zp,lists=zl,parent='apdc_cw_detail',dirty='apdc_cw_detail_ui_revision')
    legend=icon('apdc_cw_legend_swatch',0,6,'GFX_APDC_cw_swatches')+text('apdc_cw_legend_name',24,0,'APDC_CW_LEGEND',185,28,'hoi_18mbs')+button('apdc_cw_legend_hit',0,0,size=(215,28),tip='APDC_CW_LEGEND_TIP')
    ui.append(block('containerWindowType','name = "apdc_cw_legend_entry" size = { width = 215 height = 29 }\n'+legend))
    law=icon('apdc_cw_law_bg',0,0,'GFX_APDC_cw_law','alwaystransparent = yes')+text('apdc_cw_law_name',14,0,'APDC_CW_LAW_NAME',220,36,'hoi_18mbs')
    local['APDC_CW_LAW_COST']='[APDCCWSwitchCost]'
    local['APDC_CW_COST_Y']='§Y£pol_power [?apdc_cw_law_execute_cost^apdc_cw_law_row|0]§!'
    local['APDC_CW_COST_R']='§R£pol_power [?apdc_cw_law_execute_cost^apdc_cw_law_row|0]§!'
    law+=text('apdc_cw_law_cost',215,0,'APDC_CW_LAW_COST',80,36,'hoi_16mbs',extra='format = right')
    lp='';lt='';le=''
    for state,x in [('execute',300),('stop',397)]:
        law+=icon('apdc_cw_law_'+state+'_art',x,3,'GFX_APDC_cw_option','alwaystransparent = yes')
        law+=icon('apdc_cw_law_'+state+'_disabled',x,3,'GFX_APDC_cw_option_disabled','alwaystransparent = yes')
        law+=button('apdc_cw_law_'+state,x,3,'GFX_APDC_cw_law_option_feedback',size=(92,30))
        law+=text('apdc_cw_law_'+state+'_label',x,3,'APDC_CW_'+state.upper(),92,30,'hoi_18mbs',extra='format = center')
        opt=1 if state=='execute' else 0
        lp+=block('apdc_cw_law_'+state+'_art','frame = apdc_cw_law_'+state+'_frame^apdc_cw_law_row')
        unavailable='OR = { check_variable = { apdc_cw_law_locked^apdc_cw_law_row = 1 } AND = { NOT = { check_variable = { apdc_cw_law_running^apdc_cw_law_row = '+str(opt)+' } } check_variable = { political_power < apdc_cw_law_execute_cost^apdc_cw_law_row } } }'
        lt+=block('apdc_cw_law_'+state+'_disabled_visible',unavailable)
        lt+=block('apdc_cw_law_'+state+'_click_enabled','NOT = { '+unavailable+' } NOT = { check_variable = { apdc_cw_law_running^apdc_cw_law_row = '+str(opt)+' } }')
        le+=block('apdc_cw_law_'+state+'_click',setv('apdc_cw_option',opt)+'apdc_cw_submit_law = yes')
    ui.append(block('containerWindowType','name = "apdc_cw_law_entry" size = { width = 499 height = 40 }\n'+law))
    control='';active_tabs='';tab_labels='';cp=lp;ct=lt;ce=le
    for i,a in enumerate(AXES,1):
        x=16+(i-1)*175
        # Same layering as cooperation: buttons below the page, selected plate above.
        control+=button(f'apdc_cw_tab_{i}',x,0,'GFX_APDC_cw_tabs',size=(171,59))
        active_tabs+=icon(f'apdc_cw_tab_{i}_active',x,0,'GFX_APDC_cw_tabs','alwaystransparent = yes')
        tab_labels+=text(f'apdc_cw_tab_{i}_label',x,4,'APDC_CW_'+a.upper(),171,48,'hoi_24header',extra='format = center')
        ct+=block(f'apdc_cw_tab_{i}_active_visible',f'check_variable = {{ apdc_cw_tab = {i} }}')
        ce+=block(f'apdc_cw_tab_{i}_click',setv('apdc_cw_tab',i)+'apdc_cw_refresh_view = yes')
    control+=icon('apdc_cw_control_background',19,54,'GFX_APDC_cw_control','alwaystransparent = yes')+active_tabs+tab_labels
    pie=''
    for i in range(360):
        pie+=icon(f'apdc_cw_pie_{i}',0,0,'GFX_APDC_cw_pie_0',f'centerposition = yes rotation = {i*math.pi/180:.10f} pdx_tooltip = "APDC_CW_PIE_{i}"')
        cp+=block(f'apdc_cw_pie_{i}',f'image = "[APDCCWPieImage{i}]" frame = apdc_cw_pie_color^{i}')
    control+=block('containerWindowType','name = "apdc_cw_pie" position = { x = 164 y = 194 } size = { width = 0 height = 0 } scale = 0.93 clipping = no\n'+pie)
    # Same centre as the pie, but outside its 0.93-scaled container: original
    # 256x256 artwork overlays the sectors without shrinking or blocking input.
    control+=icon('apdc_cw_pie_frame',164,194,'GFX_APDC_cw_pie_frame','centerposition = yes alwaystransparent = yes')
    control+=block('containerWindowType','name = "apdc_cw_legend_scroll" position = { x = 315 y = 72 } size = { width = 215 height = 252 } clipping = yes verticalScrollbar = "right_vertical_slider" autohide_scrollbars = yes\n'+block('gridBoxType','name = "apdc_cw_legend_list" slotsize = { width = 215 height = 29 } size = { width = 215 height = 252 } max_slots_horizontal = 1 add_horizontal = no format = "UPPER_LEFT"'))
    control+=block('containerWindowType','name = "apdc_cw_law_scroll" position = { x = 545 y = 70 } size = { width = 517 height = 256 } clipping = yes verticalScrollbar = "right_cabinet_vertical_slider" autohide_scrollbars = yes scroll_wheel_factor = 40 smooth_scrolling = yes margin = { top = 0 right = 18 bottom = 0 }\nbackground = { name = "apdc_cw_law_scroll_bg" spriteType = "GFX_tiled_window_transparent" }\n'+block('gridBoxType','name = "apdc_cw_law_list" position = { x = 0 y = 0 } slotsize = { width = 499 height = 40 } size = { width = 499 height = 100% } max_slots_horizontal = 1 add_horizontal = no format = "UPPER_LEFT"'))
    control+=text('apdc_cw_empty_laws',565,150,'APDC_CW_NO_LAWS',460,35,'hoi_18mbs',extra='format = center')
    ct+='apdc_cw_empty_laws_visible = { check_variable = { apdc_cw_visible_laws^num = 0 } }\napdc_cw_legend_name_visible = { check_variable = { apdc_cw_ui_shares^apdc_cw_legend_id > 0 } }\napdc_cw_legend_swatch_visible = { check_variable = { apdc_cw_ui_shares^apdc_cw_legend_id > 0 } }\napdc_cw_legend_hit_visible = { check_variable = { apdc_cw_ui_shares^apdc_cw_legend_id > 0 } }'
    cp+='apdc_cw_legend_swatch = { frame = apdc_cw_ui_palette^apdc_cw_legend_id }'
    ui.append(block('containerWindowType','name = "apdc_cw_controls" position = { x = 0 y = 617 } size = { width = 1078 height = 350 } clipping = no\n'+control))
    scripted('apdc_cw_controls','apdc_cw_controls','always = yes',cp,ct,ce,'apdc_cw_legend_list = { array = apdc_cw_legend_rows value = apdc_cw_legend_id entry_container = "apdc_cw_legend_entry" }\napdc_cw_law_list = { array = apdc_cw_visible_laws value = apdc_cw_law_row entry_container = "apdc_cw_law_entry" }',parent='apdc_cw_panel',dirty='apdc_cw_control_ui_revision')
    short_names={'GER':'德国','FRA':'法国','LLU':'低地联盟','SOV':'苏联'}
    for tag,label in short_names.items():local['APDC_CW_SHORT_'+tag]=label
    dt('APDCCWLegendName',[('check_variable = { apdc_cw_legend_id = 0 }','APDC_CW_LEGEND_SELF')]+[(f'var:apdc_cw_ui_sources^apdc_cw_legend_id = {{ tag = {tag} }}','APDC_CW_SHORT_'+tag) for tag in short_names]+[('','APDC_CW_LEGEND_COUNTRY')])
    dt('APDCCWFaction',[('var:apdc_cw_selected = { is_in_faction = yes }','APDC_CW_FACTION_NAME'),('','APDC_CW_NONE')])
    statuses=['未获承认','附属国','弱国','小国','地区性大国','国际性大国']
    for i,v in enumerate(statuses,1):local[f'APDC_CW_STATUS_{i}']=v
    dt('APDCCWStatus',[(f'check_variable = {{ apdc_cw_ui_status = {i} }}',f'APDC_CW_STATUS_{i}') for i in range(1,7)])
    ideas=[n.key for top in __import__('common').parse((ROOT/'common/ideas/APDC_economic_systems.txt').read_text('utf-8-sig')) for group in top.children for n in group.children]
    dt('APDCCWEconomy',[(f'var:apdc_cw_selected = {{ has_idea = {idea} }}',idea) for idea in ideas]+[('','APDC_CW_NONE')])
    dt('APDCCWOrganization',[(f'var:apdc_cw_selected = {{ APDC_has_cooperation_organization = yes var:APDC_cooperation_organization_container = {{ check_variable = {{ APDC_cooperation_organization_name_id = {i} }} }} }}',key) for i,key in [(1,'APDC_COOPERATION_ORGANIZATION_FIFTH_INTERNATIONAL'),(2,'APDC_COOPERATION_ORGANIZATION_INTERNATIONAL_ROSSARTRISM')]]+[('var:apdc_cw_selected = { APDC_has_cooperation_organization = yes }','APDC_COOPERATION_ORGANIZATION_GENERIC'),('','APDC_CW_NONE')])
    for a,fn in zip(AXES,['Political','Economic','Military']):
        local['APDC_CW_LEAN_'+a]=f'亲[?apdc_cw_ui_leader_{a}.GetName]'
        for tag,label in short_names.items():local['APDC_CW_LEAN_'+tag]='亲'+label
        dt('APDCCW'+fn+'Lean',[(f'var:apdc_cw_ui_leader_{a} = {{ tag = var:PREV.apdc_cw_selected }}','APDC_CW_AUTONOMY')]+[(f'var:apdc_cw_ui_leader_{a} = {{ tag = {tag} }}','APDC_CW_LEAN_'+tag) for tag in short_names]+[('','APDC_CW_LEAN_'+a)])
    dt('APDCCWSwitchCost',[('check_variable = { political_power < apdc_cw_law_execute_cost^apdc_cw_law_row }','APDC_CW_COST_R'),('','APDC_CW_COST_Y')])
    for key in ['APDC_CW_LAW_EXECUTE_COST','APDC_CW_LAW_STOP_COST','APDC_CW_EXECUTE_COST_Y','APDC_CW_EXECUTE_COST_R','APDC_CW_STOP_COST_Y','APDC_CW_STOP_COST_R']:
        local.pop(key,None)
    laws=json.loads((ROOT/'tools/cold_war/laws.json').read_text('utf-8'))
    for law in laws:
        local[law['name']]=law['title']
        local[law['description']]=law['description_text']
    dt('APDCCWLawName',[(f'check_variable = {{ apdc_cw_law_id^apdc_cw_law_row = {law["id"]} }}',law['name']) for law in laws]+[('','APDC_CW_EMPTY')])
    dt('APDCCWLawDescription',[(f'check_variable = {{ apdc_cw_law_id^apdc_cw_law_row = {law["id"]} }}',law['description']) for law in laws]+[('','APDC_CW_EMPTY')])
    write('interface/APDC_cold_war.gui',block('guiTypes',''.join(ui)))
    write('common/scripted_guis/APDC_cold_war.txt',block('scripted_gui',''.join(sg)))
    write('common/scripted_localisation/APDC_cold_war.txt',''.join(defined))
    # Always use valid localization escapes rather than literal newlines.
    write('localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml','l_simp_chinese:\n'+''.join(' '+k+':0 "'+v.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"\n' for k,v in local.items()))

if __name__=='__main__':build()
