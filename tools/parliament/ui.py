"""Native scripted GUI: persistent seats, main panel and sliding subpanels."""
from common import *


def icon(name,sprite,x,y,more=''):
    return block('iconType','name = "'+name+'" position = { x = '+str(x)+' y = '+str(y)+' } spriteType = "'+sprite+'" '+more)


def text(name,key,x,y,w,h=24,font='hoi_18mbs',more=''):
    if 'alwaystransparent' not in more and 'pdx_tooltip' not in more:more+=' alwaystransparent = yes'
    return block('instantTextboxType','name = "'+name+'" position = { x = '+str(x)+' y = '+str(y)+' } font = "'+font+'" text = "'+key+'" maxWidth = '+str(w)+' maxHeight = '+str(h)+' truncate = no format = left '+more)


def button(name,sprite,x,y,w,h,tooltip='',more=''):
    return block('buttonType','name = "'+name+'" position = { x = '+str(x)+' y = '+str(y)+' } size = { x = '+str(w)+' y = '+str(h)+' } spriteType = "'+sprite+'" clicksound = click_default '+('pdx_tooltip = "'+tooltip+'" ' if tooltip else '')+more)


def window(name,body,attrs=''):
    if 'position' not in attrs:attrs='position = { x = 0 y = 0 } '+attrs
    return block('containerWindowType','name = "'+name+'" '+attrs+'\n'+body)


def scripted(name,window_name,body,attrs=''):
    return block(name,'context_type = player_context\nwindow_name = "'+window_name+'"\n'+attrs+'\n'+body)


def defined(name,rows,default):
    return block('defined_text','name = '+name+'\n'+''.join(block('text','trigger = { '+cond+' }\nlocalization_key = '+key) for cond,key in rows)+block('text','localization_key = '+default))


def merge_list_rows(sgui):
    # Native dynamic rows inherit their owner's context. A separate scripted
    # GUI would also instantiate the row as an unrelated top-level window.
    owners={P+'candidate_row_ui':P+'candidate_panel_ui',P+'reform_row_ui':P+'panel_ui',P+'special_row_ui':P+'panel_ui',P+'option_row_ui':P+'law_side_ui'}
    nodes=parse(sgui); merged={}
    for row,owner in owners.items():
        n=next(n for n in nodes if n.key==row)
        for group in ('properties','effects','triggers'):
            c=n.get(group)
            if c:merged.setdefault((owner,group),[]).extend(sgui[v.start:v.end] for v in c.children)
    out=''
    for n in nodes:
        if n.key in owners:continue
        body=''
        for c in n.children:
            if (n.key,c.key) in merged:
                body+=block(c.key,'\n'.join([sgui[v.start:v.end] for v in c.children]+merged.pop((n.key,c.key))))
            else:body+=sgui[c.start:c.end]+'\n'
        for key in [k for k in merged if k[0]==n.key]:body+=block(key[1],'\n'.join(merged.pop(key)))
        out+=block(n.key,body)
    assert not merged
    return out


def generate(loc):
    groups=load_json('laws.json')['groups'];regimes=load_json('regimes.json');settings=load_json('settings.json')
    layout=load_json('seat_layout.json')['points']
    gui='';sgui='';defs='';ui_effects=''
    loc.update({
        P+'empty':'',P+'no_agenda':'暂无议案',P+'open_tip':'§Y[ApdcParlAssemblyName]§!\n§W点击打开§!§G议会面板§!',
        P+'election_heading':'下次议会选举：',P+'no_elections':'无选举',P+'election_date':'[?apdc_parl_next_year|0]年[?apdc_parl_next_month|0]月[?apdc_parl_next_day|0]日',
        P+'current_bill':'当前议案：[ApdcParlBillName]',P+'support_label':'议案支持率：[ApdcParlSupportColor][?apdc_parl_support|1]%§!',
        P+'stage_label':'当前阶段：[ApdcParlStageName]',P+'remaining_label':'剩余时间：[ApdcParlRemaining]',P+'remaining_days':'[?apdc_parl_remaining_display|0]天',P+'paused':'暂停',
        P+'stage_0':'—',P+'stage_1':'宣读',P+'stage_2':'辩论',P+'stage_3':'审议',
        P+'green':'§G',P+'red':'§R',P+'yellow':'§Y',
        P+'reforms':'政治改革',P+'specials':'特殊议案',P+'negotiate':'谈判',P+'ban':'封禁',P+'unban':'解封',P+'propose':'提案',P+'dismiss':'解除任命',
        P+'cost_member':'£pol_power §Y'+str(settings['member_cost'])+'§!',P+'cost_chief':'£pol_power §Y'+str(settings['chief_cost'])+'§!',P+'cost_free':'§G免费任命§!',
        P+'candidate_name':'[ApdcParlCandidateName]',P+'candidate_trait':'[ApdcParlCandidateTrait]',P+'appointment_cost':'[ApdcParlAppointmentCost]',
        P+'candidate_tip':'§Y[ApdcParlCandidateName]§!\n[ApdcParlCandidateTrait]\n[ApdcParlCandidateEffects]\n\n[ApdcParlAppointmentCost]',
        P+'candidate_header':'[ApdcParlCandidateHeader]',P+'candidate_quota':'[ApdcParlCandidateQuota]',
        P+'selected_office':'[ApdcParlSelectedOffice]',P+'prime':'总理',P+'deputy':'副总理',P+'member':'内阁成员',P+'no_candidates':'暂无已登记的候选人',
        P+'ban_tip':'将该党派的封禁或解封提上议程。执政党及执政联盟成员受保护。',
        P+'negotiate_tip':'在当前议案中与该党派谈判。需要该党派在议会中拥有席位。',
        P+'support_tip':'§W基础法案支持率：§Y50%§![ApdcParlContribution0][ApdcParlContribution1][ApdcParlContribution2][ApdcParlContribution3][ApdcParlContribution4][ApdcParlContribution5][ApdcParlContribution6][ApdcParlContribution7][ApdcParlContribution8]',
        P+'reform_current':'[ApdcParlReformCurrent]',P+'reform_title':'[ApdcParlReformTitle]',P+'law_option_name':'[ApdcParlOptionName]',P+'law_option_tip':'[ApdcParlOptionTooltip]',
        P+'law_option_cost':'[ApdcParlProposalCost]',P+'proposal_cost_enough':'£pol_power §Y'+str(settings['proposal_cost'])+'§!',P+'proposal_cost_short':'£pol_power §R'+str(settings['proposal_cost'])+'§!',P+'current_option':'§Y当前法案§!',
        P+'special_name':'[ApdcParlSpecialName]',P+'special_cost':'£pol_power §Y[?apdc_parl_special_costs^apdc_parl_special_context|0]§!',
        P+'special_desc':'[ApdcParlSpecialDescription]',
        P+'close':'关闭议会面板',P+'side_close_tip':'关闭法案选择',P+'side_title':'[ApdcParlSelectedGroupName]'
    })
    defs+=defined('ApdcParlAssemblyName',[(ck('regime','=',i),P+'assembly_'+str(i)) for i in range(1,10)],P+'assembly_4')
    defs+=defined('ApdcParlRegimeIcon',[(ck('regime','=',i),'GFX_apdc_parl_regime_'+key) for i,key in enumerate(regimes,1)],'GFX_apdc_parl_regime_parliamentary_republic')
    defs+=defined('ApdcParlRegimeTooltip',[(ck('regime','=',i),P+'regime_tip_'+str(i)) for i in range(1,10)],P+'empty')
    defs+=defined('ApdcParlElectionDate',[(ck('elections_enabled','=',0),P+'no_elections')],P+'election_date')
    defs+=defined('ApdcParlStageName',[(ck('stage','=',i),P+'stage_'+str(i)) for i in range(1,4)],P+'stage_0')
    defs+=defined('ApdcParlSupportColor',[(ck('support','>',0),P+'green'),(ck('support','<',0),P+'red')],P+'yellow')
    defs+=defined('ApdcParlRemaining',[(ck('agenda','=',0),P+'stage_0'),(ck('support_speed','<=',0),P+'paused')],P+'remaining_days')
    defs+=defined('ApdcParlAppointmentCost',[(ck('selected_role','=',7)+' '+ck('free_prime','=',1),P+'cost_free'),(ck('selected_role','=',8)+' '+ck('free_deputy','=',1),P+'cost_free'),(ck('selected_role','>',6),P+'cost_chief')],P+'cost_member')
    defs+=defined('ApdcParlProposalCost',[('has_political_power < '+str(settings['proposal_cost']),P+'proposal_cost_short')],P+'proposal_cost_enough')
    loc[P+'law_option_tip']='[ApdcParlOptionTooltip]\n\n更换花费：[ApdcParlProposalCost]\n有议程正在进行时禁止更换。'
    defs+=defined('ApdcParlSelectedOffice',[(ck('selected_role','=',7),P+'prime'),(ck('selected_role','=',8),P+'deputy')],P+'member')
    for i,(key,r) in enumerate(regimes.items(),1):
        loc[P+'assembly_'+str(i)]=r['assembly_name']
        loc[P+'regime_tip_'+str(i)]='§Y'+r['name']+'§!\n§W议案审议时间：§G'+('立刻' if not r['base_days'] else str(r['base_days'])+'§!§W天')+'§!\n§W党派提供加成：§G'+str(round(r['party_bonus_factor']*100))+'%§!\n§W党派反对权：§G'+str(round(r['opposition_factor']*100))+'%§!'
    bill_rows=[];option_rows=[];option_tip_rows=[];current_rows=[];title_rows=[];icon_rows=[]
    for g in groups:
        title_rows.append((ck('group_context','=',g['id']),P+'group_'+str(g['id'])))
        for o in g['options']:
            key=P+'law_'+g['key']+'_'+str(o['id'])
            bill_rows.append((ck('bill_kind','=',1)+' '+ck('bill_target','=',g['id'])+' '+ck('bill_option','=',o['id']),key))
            option_rows.append((ck('option_context','=',g['id']*1000+o['id']),key))
            option_tip_rows.append((ck('option_context','=',g['id']*1000+o['id']),key+'_tip'))
            current_rows.append((ck('group_context','=',g['id'])+' '+ck('law_'+str(g['id']),'=',o['id']),key))
            if g['id']==5:
                eco=json.loads(read('docs/parliament/20261107-design/opening_policy.json'))['economic_names']
                sprite='GFX_APDC_economic_system_'+next(k for k,v in eco.items() if v==o['name'])
            elif g['id']==6:sprite='GFX_apdc_parl_regime_'+list(regimes)[o['id']-1]
            else:sprite='GFX_idea_generic_build_infrastructure'
            icon_rows.append((ck('group_context','=',g['id'])+' '+ck('law_'+str(g['id']),'=',o['id']),sprite))
    for i,p in enumerate(PARTIES,1):
        loc[P+'bill_ban_'+p]='封禁'+NAMES[i-1]
        loc[P+'bill_unban_'+p]='解封'+NAMES[i-1]
        bill_rows.extend([(ck('bill_kind','=',2)+' '+ck('bill_target','=',i),P+'bill_ban_'+p),(ck('bill_kind','=',3)+' '+ck('bill_target','=',i),P+'bill_unban_'+p)])
    defs+=defined('ApdcParlSpecialName',[], '[?apdc_parl_special_names^apdc_parl_special_context.GetTokenKey]')
    defs+=defined('ApdcParlSpecialDescription',[], '[?apdc_parl_special_descriptions^apdc_parl_special_context.GetTokenKey]')
    defs+=defined('ApdcParlSpecialActiveName',[], '[?apdc_parl_special_active_name.GetTokenKey]')
    loc[P+'special_active']='[ApdcParlSpecialActiveName]'
    bill_rows.append((ck('bill_kind','=',4),P+'special_active'))
    defs+=defined('ApdcParlBillName',bill_rows,P+'no_agenda')
    defs+=defined('ApdcParlOptionName',option_rows,P+'empty')+defined('ApdcParlOptionTooltip',option_tip_rows,P+'empty')
    defs+=defined('ApdcParlReformCurrent',current_rows,P+'empty')+defined('ApdcParlReformTitle',title_rows,P+'empty')+defined('ApdcParlReformIcon',icon_rows,'GFX_idea_generic_build_infrastructure')
    defs+=defined('ApdcParlSelectedGroupName',[(ck('selected_group','=',g['id']),P+'group_'+str(g['id'])) for g in groups],P+'empty')
    # Political-page seats and the only parliament entry button.
    seats='';seat_props=''
    for i,point in enumerate(layout):
        seats+=icon(P+'entry_seat_'+str(i),'GFX_apdc_parl_dot_small',round(116+point['x']*.47),round(511+point['y']*.47),'centerposition = yes alwaystransparent = yes')
        seat_props+=P+'entry_seat_'+str(i)+' = { frame = '+P+'seat_colors^'+str(i)+' }\n'
    from PIL import Image
    with Image.open(ROOT/'gfx/interface/APDC/parliament/entry.png') as entry_art:entry_width,entry_height=entry_art.size
    seats+=button(P+'entry_button','GFX_apdc_parl_entry',98,489,entry_width,entry_height,P+'open_tip')
    gui+=window(P+'entry',seats,'position = { x = 0 y = 44 } size = { width = 215 height = 550 }')
    entry_action='if = { limit = { has_country_flag = apdc_parl_open } clr_country_flag = apdc_parl_open clr_country_flag = apdc_parl_candidate_panel_open clear_variable = apdc_parl_selected_group } else = { apdc_parl_initialize = yes apdc_parl_refresh_special_catalogue = yes apdc_parl_refresh = yes APDC_update_cabinet_statistics = yes set_country_flag = apdc_parl_open }'
    sgui+=scripted(P+'entry_ui',P+'entry',block('properties',seat_props)+block('effects',P+'entry_button_click = { '+entry_action+op('dirty','add',1)+' }')+'visible = { always = yes }','parent_window_token = politics_tab\ndirty = '+P+'dirty')
    # Shared option row and special rows.
    # Use the actual economic selector, including button/icon hit regions,
    # row metrics, fonts, alignment, scrolling and slide animation.
    economic=read('interface/APDC_economy_panel.gui')
    economic_windows={n.val('name'):n for o in parse(economic) for n in o.children}
    rename={'APDC_eco_law_row':P+'option_row','APDC_eco_law_side':P+'law_side','APDC_eco_law_scroll':P+'option_scroll','APDC_eco_law_list':P+'option_list','APDC_eco_law_button':P+'option_button','APDC_eco_law_current':P+'option_current','APDC_eco_law_icon':P+'option_icon','APDC_eco_law_name':P+'option_name','APDC_eco_law_cost':P+'option_cost','APDC_eco_law_title':P+'side_title','APDC_eco_law_close':P+'side_close','APDC_ECO_LAW_TOOLTIP':P+'law_option_tip','APDC_ECO_LAW_NAME':P+'law_option_name','APDC_ECO_LAW_COST':P+'law_option_cost','APDC_ECO_LAW_TITLE':P+'side_title','APDC_ECO_CLOSE':P+'side_close_tip'}
    for name in ['APDC_eco_law_row','APDC_eco_law_side']:
        node=economic_windows[name];raw=economic[node.start:node.end]
        for old,new in sorted(rename.items(),key=lambda v:-len(v[0])):raw=raw.replace(old,new)
        raw=raw.replace('"GFX_idea_entry_bg_3"','"GFX_apdc_parl_law_option_card"')
        gui+=raw+'\n'
    row=icon(P+'special_background','GFX_apdc_parl_special_row',0,0,'alwaystransparent = yes')+text(P+'special_name',P+'special_name',10,8,250,25)+text(P+'special_cost',P+'special_cost',260,8,130,25,'hoi_16mbs')+button(P+'special_submit','GFX_apdc_parl_special_button',390,3,91,31,P+'special_desc')+text(P+'special_submit_text',P+'propose',418,7,60,22,'hoi_18mbs','alwaystransparent = yes')
    gui+=window(P+'special_entry',row,'size = { width = 497 height = 49 }')
    # Four-column rows: negative IDs are full-width party headers, zeros are
    # transparent spacers, positive IDs are the unchanged candidate card style.
    row=text(P+'candidate_header',P+'candidate_header',30,0,980,28,'APDC_cabinet_24')+text(P+'candidate_quota',P+'candidate_quota',90,34,850,26,'hoi_20b')
    row+=button(P+'candidate_button','GFX_apdc_parl_candidate_card',0,0,230,80,P+'candidate_tip')
    row+=icon(P+'candidate_portrait','GFX_leader_unknown',42,38,'centerposition = yes scale = 0.30 alwaystransparent = yes')
    row+=text(P+'candidate_name',P+'candidate_name',76,9,147,17,more='fixedsize = yes').replace('truncate = no','truncate = yes')+text(P+'candidate_trait',P+'candidate_trait',76,29,145,16,'hoi_16mbs')+text(P+'candidate_cost',P+'appointment_cost',80,51,142,16,'hoi_16mbs')
    gui+=window(P+'candidate_row',row,'size = { width = 242 height = 94 } clipping = no')
    # Reform tiles use a grid with overflow-only scrolling.
    row=button(P+'reform_button','GFX_apdc_parl_law_tile',0,0,249,73)
    row+=icon(P+'reform_icon','GFX_idea_generic_build_infrastructure',36,37,'centerposition = yes scale = 0.75 alwaystransparent = yes')
    row+=text(P+'reform_title',P+'reform_title',91,10,152,24)+text(P+'reform_current',P+'reform_current',91,38,152,26,'hoi_16mbs')
    gui+=window(P+'reform_row',row,'size = { width = 249 height = 83 }')
    grid=block('gridBoxType','name = "'+P+'candidate_list" position = { x = 0 y = 0 } size = { width = 990 height = 100% } slotsize = { width = 242 height = 94 } max_slots_horizontal = 4 format = "UPPER_LEFT"')
    scroll=window(P+'candidate_scroll',grid,'position = { x = 30 y = 18 } size = { width = 1030 height = 305 } clipping = yes verticalScrollbar = "right_vertical_slider" autohide_scrollbars = yes smooth_scrolling = yes scroll_wheel_factor = 74 margin = { top = 0 right = 18 bottom = 0 }')
    dismiss=button(P+'dismiss','GFX_apdc_parl_party_button',506,341,67,24)+text(P+'dismiss_text',P+'dismiss',506,343,67,20,'hoi_16mbs','fixedsize = yes').replace('format = left','format = center')
    gui+=window(P+'candidate_panel','background = { name = "Background" spriteType = "GFX_apdc_parl_candidate_background" }\n'+text(P+'no_candidates',P+'no_candidates',390,150,460,24)+scroll+dismiss,
                'position = { x = 0 y = 377 } show_position = { x = 0 y = 0 } size = { width = 1078 height = 377 } show_animation_type = decelerated hide_animation_type = accelerated animation_time = 300 clipping = yes')
    # Main shell: sidebar behind body; upward candidate hook above lower lists.
    main=window(P+'law_hook','','position = { x = 0 y = 0 } size = { width = 1078 height = 972 } clipping = no')
    main+='background = { name = "Background" spriteType = "GFX_apdc_parl_background" }\n'
    main+=icon(P+'regime','GFX_apdc_parl_regime_parliamentary_republic',166,121,'centerposition = yes scale = 1.4 pdx_tooltip = "apdc_parl_regime_tooltip"')
    loc[P+'regime_tooltip']='[ApdcParlRegimeTooltip]'
    main+=text(P+'election_heading',P+'election_heading',265,98,185,25,'hoi_20b')+text(P+'election_date','[ApdcParlElectionDate]',265,128,185,30)
    props=P+'regime = { image = "[ApdcParlRegimeIcon]" }\n'
    for r,x in [(7,455),(8,545)]:
        main+=button(P+'role_button_'+str(r),'GFX_apdc_parl_hit_74_98',x,73,74,98,'APDC_PRIME_MINISTER_TOOLTIP' if r==7 else 'APDC_DEPUTY_PRIME_MINISTER_TOOLTIP')+icon(P+'role_portrait_'+str(r),'GFX_leader_unknown',x+37,122,'centerposition = yes scale = 0.47 alwaystransparent = yes')
        props+=P+'role_portrait_'+str(r)+' = { image = "[ApdcParlRole'+str(r)+'Portrait]" }\n'
    for r in range(1,7):
        x=52+95*((r-1)%3);y=244+101*((r-1)//3)
        main+=button(P+'role_button_'+str(r),'GFX_apdc_parl_hit_47_63',x,y,47,63,'APDC_CABINET_SLOT_'+str(r)+'_TOOLTIP')+icon(P+'role_portrait_'+str(r),'GFX_apdc_parl_empty_slot',x+24,y+32,'centerposition = yes scale = 0.30 alwaystransparent = yes')
        props+=P+'role_portrait_'+str(r)+' = { image = "[ApdcParlRole'+str(r)+'Portrait]" }\n'
    for i,point in enumerate(layout):
        main+=icon(P+'seat_'+str(i),'GFX_apdc_parl_dot_large',round(540+point['x']),round(428+point['y']),'centerposition = yes alwaystransparent = yes')
        props+=P+'seat_'+str(i)+' = { frame = '+P+'seat_colors^'+str(i)+' }\n'
    # Reuse the existing coalition pie and legend unchanged except position/scale.
    legacy=read('tools/parliament/legacy/APDC_cabinet.gui')
    old_panel=next(n for outer in parse(legacy) if outer.key=='guiTypes' for n in outer.children if n.val('name')=='APDC_cabinet_member_panel')
    legend_triggers=''
    for n in old_panel.children:
        name=n.val('name','')
        if name=='APDC_cabinet_pie_slices':
            raw=legacy[n.start:n.end]
            import re
            raw=re.sub(r'position\s*=\s*\{\s*x\s*=\s*810\s+y\s*=\s*125\s*\}', 'position = { x = 736 y = 120 }',raw, count=1)
            main+=raw+'\n'
        elif name=='APDC_cabinet_pie_overlay':
            raw=legacy[n.start:n.end]
            raw=re.sub(r'position\s*=\s*\{\s*x\s*=\s*810\s+y\s*=\s*125\s*\}', 'position = { x = 736 y = 120 }',raw,count=1)
            main+=raw+'\n'
    for i,p in enumerate(PARTIES):
        legacy_index=['communism','socialism','social_democracy','conservatism','liberalism','authoritarianism','dictatorship','fascism','fundamentalism'].index(p)
        main+=icon(P+'legend_swatch_'+p,'GFX_APDC_cabinet_ideology_swatch',833,57+i*14,'frame = '+str(legacy_index+1)+' alwaystransparent = yes')
        main+=text(P+'legend_name_'+p,'APDC_CABINET_PARTY_'+p.upper()+'_COLORED',850,55+i*14,205,18,'hoi_16mbs')
        legend_triggers+=P+'legend_swatch_'+p+'_visible = { has_country_flag = APDC_governing_coalition_'+p+' }\n'+P+'legend_name_'+p+'_visible = { has_country_flag = APDC_governing_coalition_'+p+' }\n'
    for i in range(100):props+='APDC_cabinet_pie_'+str(i)+' = { frame = APDC_cabinet_pie^'+str(i)+' }\n'
    for i,p in enumerate(PARTIES):
        y=188+i*28
        legacy_index=['communism','socialism','social_democracy','conservatism','liberalism','authoritarianism','dictatorship','fascism','fundamentalism'].index(p)
        main+=icon(P+'party_swatch_'+p,'GFX_APDC_cabinet_ideology_swatch',744,y+5,'frame = '+str(legacy_index+1)+' alwaystransparent = yes')
        main+=button(P+'party_hit_'+p,'GFX_apdc_parl_hit_150_24',758,y+2,150,24,P+'party_tip_'+p)+text(P+'party_name_'+p,'APDC_CABINET_PARTY_'+p.upper()+'_COLORED',762,y+2,143,24,'hoi_16mbs','alwaystransparent = yes')
        main+=button(P+'negotiate_'+p,'GFX_apdc_parl_party_button',908,y,67,24,P+'negotiate_tip')+text(P+'negotiate_label_'+p,P+'negotiate',925,y+2,48,22,'hoi_16mbs','alwaystransparent = yes')
        main+=button(P+'ban_'+p,'GFX_apdc_parl_party_button',985,y,67,24)+text(P+'ban_label_'+p,'[ApdcParlBan'+str(i)+']',1002,y+2,48,22,'hoi_16mbs','alwaystransparent = yes')
        defs+=defined('ApdcParlBan'+str(i),[('has_country_flag = '+P+'banned_'+p,P+'unban')],P+'ban')
    main+=text(P+'bill',P+'current_bill',40,475,550,25)+text(P+'support',P+'support_label',40,500,300,25,'hoi_18mbs','pdx_tooltip = "apdc_parl_support_tip"')+text(P+'stage',P+'stage_label',40,525,350,25)+text(P+'remaining',P+'remaining_label',40,550,350,25)
    for i in range(10):
        main+=icon(P+'progress_'+str(i),'GFX_apdc_parl_progress_'+str(i),34+i*101,578,'alwaystransparent = yes')
        props+=P+'progress_'+str(i)+' = { frame = '+P+'progress_frame_'+str(i)+' }\n'
    for i,x in [(1,371),(2,706)]:
        main+=icon(P+'latch_'+str(i),'GFX_apdc_parl_latches',x,582,'centerposition = yes alwaystransparent = yes')
        props+=P+'latch_'+str(i)+' = { frame = '+P+'latch_'+str(i)+' }\n'
    main+=text(P+'reforms_title',P+'reforms',40,621,250,25,'hoi_20b')+text(P+'specials_title',P+'specials',964,621,100,25,'hoi_20b')
    for which,x,w,entry,roww,rowh,columns in [('reforms',15,518,'reform',249,83,2),('specials',547,515,'special',497,49,1)]:
        grid=block('gridBoxType','name = "'+P+which+'_list" position = { x = 0 y = 0 } size = { width = '+str(w-18)+' height = 290 } slotsize = { width = '+str(roww)+' height = '+str(rowh)+' } max_slots_horizontal = '+str(columns)+' format = "UPPER_LEFT"')
        main+=window(P+which+'_scroll',grid,'position = { x = '+str(x)+' y = 657 } size = { width = '+str(w)+' height = 290 } clipping = yes verticalScrollbar = "right_vertical_slider" autohide_scrollbars = yes smooth_scrolling = yes scroll_wheel_factor = 74 margin = { top = 0 right = 18 bottom = 0 }')
    main+=window(P+'candidate_hook','','position = { x = 0 y = 595 } size = { width = 1078 height = 377 } clipping = yes')
    main+=button(P+'close','GFX_APDC_custom_panel_exit',12,11,96,47,P+'close','shortcut = "ESCAPE"')
    gui+=window(P+'panel',main,'position = { x = -250 y = 0 } size = { width = 1078 height = 972 } orientation = center origo = center moveable = yes click_to_front = yes clipping = no')
    clicks=P+'close_click = { clr_country_flag = '+P+'open clr_country_flag = '+P+'candidate_panel_open clear_variable = '+P+'selected_group clear_variable = APDC_cabinet_selected_slot '+op('dirty','add',1)+' }\n'
    for r in range(1,9):clicks+=P+'role_button_'+str(r)+'_click = { apdc_parl_select_role = { ROLE = '+str(r)+' } }\n'
    trigger=legend_triggers
    for p in PARTIES:
        clicks+=P+'negotiate_'+p+'_click = { '+sv('negotiating_party',PARTIES.index(p)+1)+'country_event = { id = apdc_parliament.1 } }\n'
        clicks+=P+'ban_'+p+'_click = { if = { limit = { has_country_flag = '+P+'banned_'+p+' } apdc_parl_submit_unban_'+p+' = yes } else = { apdc_parl_submit_ban_'+p+' = yes } }\n'
        trigger+=P+'negotiate_'+p+'_click_enabled = { '+ck('agenda','>',0)+' '+ck('seats_'+p,'>',0)+' }\n'
        trigger+=P+'ban_'+p+'_click_enabled = { apdc_parl_can_submit = yes OR = { has_country_flag = '+P+'banned_'+p+' apdc_parl_can_ban_'+p+' = yes } }\n'
    lists=''
    for which,array,value,entry in [('reforms','reform_groups','value = '+P+'group_context','reform_row'),('specials','special_ids','index = '+P+'special_context','special_entry')]:
        lists+=block(P+which+'_list','array = '+P+array+' '+value+' entry_container = "'+P+entry+'"')
    sgui+=scripted(P+'panel_ui',P+'panel','visible = { has_country_flag = '+P+'open }\n'+block('properties',props)+block('effects',clicks)+block('triggers',trigger)+block('dynamic_lists',lists),'dirty = '+P+'dirty')
    occupied=[]
    for role in range(1,9):
        value=ck('role_'+str(role),'>',0)
        if role>6:value='OR = { '+value+' has_variable = APDC_'+('prime_minister' if role==7 else 'deputy_prime_minister')+'_character }'
        occupied.append('AND = { '+ck('selected_role','=',role)+' '+value+' }')
    sgui+=scripted(P+'candidate_panel_ui',P+'candidate_panel','visible = { has_country_flag = '+P+'open has_country_flag = '+P+'candidate_panel_open }\n'+block('effects',P+'dismiss_click = { apdc_parl_dismiss_selected = yes }')+block('triggers',P+'no_candidates_visible = { '+ck('real_candidate_count','=',0)+' }\n'+P+'dismiss_click_enabled = { OR = { '+' '.join(occupied)+' } }')+block('dynamic_lists',block(P+'candidate_list','array = '+P+'candidates value = '+P+'candidate_context entry_container = "'+P+'candidate_row"')),'parent_window_name = "'+P+'candidate_hook"\ndirty = '+P+'dirty')
    enabled=ck('candidate_context','>',0)+' check_variable = { apdc_nc_enableds^apdc_parl_candidate_context = 1 }'
    row_tr=P+'candidate_button_click_enabled = { '+enabled+' }\n'
    for name in ['candidate_button','candidate_portrait','candidate_name','candidate_trait','candidate_cost']:row_tr+=P+name+'_visible = { '+ck('candidate_context','>',0)+' }\n'
    row_tr+=P+'candidate_header_visible = { '+ck('candidate_context','<',0)+' }\n'+P+'candidate_quota_visible = { '+ck('candidate_context','<',0)+' '+ck('selected_role','<',7)+' }\n'
    sgui+=scripted(P+'candidate_row_ui',P+'candidate_row',block('properties',P+'candidate_portrait = { image = "[ApdcParlCandidatePortrait]" }')+block('triggers',row_tr)+block('effects',P+'candidate_button_click = { '+sv('selected_candidate','apdc_nc_ids^apdc_parl_candidate_context')+'apdc_parl_appoint_selected = yes }'))
    defs+=defined('ApdcParlCandidateHeader',[(ck('candidate_context','=',-i-1),'APDC_CABINET_PARTY_'+p.upper()+'_COLORED') for i,p in enumerate(PARTIES)],P+'empty')
    for p in PARTIES:loc[P+'quota_'+p]='可任命：§Y[?APDC_cabinet_available_'+p+'|0]§!    已任命：§Y[?APDC_cabinet_used_'+p+'|0]§!'
    defs+=defined('ApdcParlCandidateQuota',[(ck('candidate_context','=',-i-1),P+'quota_'+p) for i,p in enumerate(PARTIES)],P+'empty')
    refresh='clear_array = '+P+'law_options\n'
    for g in groups:refresh+=iff(ck('selected_group','=',g['id']),''.join('add_to_array = { '+P+'law_options = '+str(g['id']*1000+o['id'])+' }\n' for o in g['options']))
    ui_effects+=effect('refresh_law_options',refresh+op('dirty','add',1))
    click=sv('selected_group',var('group_context'))+'apdc_parl_refresh_law_options = yes\n'
    sgui+=scripted(P+'reform_row_ui',P+'reform_row',block('properties',P+'reform_icon = { image = "[ApdcParlReformIcon]" }')+block('effects',P+'reform_button_click = { '+click+' }'))
    sgui+=scripted(P+'law_side_ui',P+'law_side','visible = { has_country_flag = '+P+'open has_variable = '+P+'selected_group }\n'+block('effects',P+'side_close_click = { clear_variable = '+P+'selected_group '+op('dirty','add',1)+' }')+block('dynamic_lists',block(P+'option_list','array = '+P+'law_options value = '+P+'option_context entry_container = "'+P+'option_row"')),'parent_window_name = "'+P+'law_hook"\ndirty = '+P+'dirty')
    option_enabled=[];option_current=[];option_click=''
    for g in groups:
        for o in g['options']:
            match=ck('option_context','=',g['id']*1000+o['id'])
            current=ck('law_'+str(g['id']),'=',o['id'])
            option_enabled.append('AND = { '+match+' NOT = { '+current+' } }')
            option_current.append('AND = { '+match+' '+current+' }')
            option_click+=iff(match,P+'propose_'+g['key']+'_'+str(o['id'])+' = yes\nclear_variable = '+P+'selected_group\n')
    option_icons=[]
    for g in groups:
        for o in g['options']:
            sprite='GFX_idea_generic_build_infrastructure'
            if g['id']==5:
                economic=json.loads(read('docs/parliament/20261107-design/opening_policy.json'))['economic_names']
                sprite='GFX_APDC_economic_system_'+next(k for k,v in economic.items() if v==o['name'])
            elif g['id']==6:sprite='GFX_apdc_parl_regime_'+list(regimes)[o['id']-1]
            option_icons.append((ck('option_context','=',g['id']*1000+o['id']),sprite))
    defs+=defined('ApdcParlOptionIcon',option_icons,'GFX_idea_generic_build_infrastructure')
    option_guard='apdc_parl_can_submit = yes has_political_power > '+str(settings['proposal_cost']-1)+' OR = { '+' '.join(option_enabled)+' }'
    sgui+=scripted(P+'option_row_ui',P+'option_row',block('properties',P+'option_icon = { image = "[ApdcParlOptionIcon]" }')+block('effects',P+'option_button_click = { '+option_click+' }\n'+P+'option_icon_click = { '+option_click+' }')+block('triggers',P+'option_button_click_enabled = { '+option_guard+' }\n'+P+'option_icon_click_enabled = { '+option_guard+' }\n'+P+'option_current_visible = { OR = { '+' '.join(option_current)+' } }'))
    sgui+=scripted(P+'special_row_ui',P+'special_entry',block('effects',P+'special_submit_click = { '+sv('selected_special_index',var('special_context'))+'apdc_parl_submit_special_bill = yes }')+block('triggers',P+'special_submit_click_enabled = { apdc_parl_can_submit = yes check_variable = { '+P+'special_enabled^'+var('special_context')+' = 1 } NOT = { has_political_power < '+P+'special_costs^'+var('special_context')+' } }'))
    # The original political-page prime/deputy display remains; its six-slot
    # buttons and the old independent selector are replaced by this system.
    original_gui=read('tools/parliament/legacy/APDC_cabinet.gui');roots=parse(original_gui)
    roles=next(n for outer in roots for n in outer.children if n.val('name')=='APDC_cabinet_roles')
    write('interface/APDC_cabinet.gui',block('guiTypes',original_gui[roles.start:roles.end]))
    original_sgui=read('tools/parliament/legacy/APDC_cabinet_scripted_gui.txt');roots=parse(original_sgui)
    roles=next(n for outer in roots for n in outer.children if n.key=='APDC_cabinet_roles')
    write('common/scripted_guis/APDC_cabinet_scripted_gui.txt',block('scripted_gui',original_sgui[roles.start:roles.end]))
    ui_effects+=effect('initialize_ui_arrays','clear_array = '+P+'reform_groups\n'+''.join('add_to_array = { '+P+'reform_groups = '+str(g['id'])+' }\n' for g in groups))
    # Native scrolling windows require a background to establish the scroll
    # content rectangle. An absent background silently drops nested grids.
    for node in reversed(list(walk(parse(gui)))):
        if node.key=='containerWindowType' and node.get('verticalScrollbar') and not node.get('background'):
            where=gui.index('\n',node.start)+1
            gui=gui[:where]+'background = { name = "Background" spriteType = "GFX_tiled_window_transparent" }\n'+gui[where:]
    write('interface/apdc_parliament.gui',block('guiTypes',gui))
    sgui=sgui.replace('entry_container = "','change_scope = no entry_container = "')
    write('common/scripted_guis/apdc_parliament.txt',block('scripted_gui',merge_list_rows(sgui)))
    write('common/scripted_localisation/apdc_parliament_ui.txt',defs)
    write('common/scripted_effects/apdc_parliament_ui.txt',ui_effects)
