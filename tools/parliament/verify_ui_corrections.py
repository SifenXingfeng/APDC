"""Check the nine requested UI corrections against their actual sources."""
import re
from common import *


def run():
    gui=read('interface/apdc_parliament.gui');sgui=read('common/scripted_guis/apdc_parliament.txt')
    windows={n.val('name'):n for o in parse(gui) for n in o.children}
    find=lambda name:next(n for n in walk(parse(gui)) if n.val('name')==name)
    checks=[]
    def check(name,test):
        assert test,name
        checks.append(name)
    main=windows[P+'panel'];candidate=windows[P+'candidate_panel']
    check('draggable_main_has_real_background',main.val('moveable')=='yes' and main.get('background') is not None)
    check('candidate_panel_background_captures_input',candidate.get('background') is not None)
    check('no_caption_added_to_candidate_panel',not any(n.val('name')==P+'selected_office' for n in walk(candidate.children)))
    dismiss=find(P+'dismiss');pos=dismiss.get('position')
    check('dismiss_bottom_center_uses_party_button',dismiss.val('spriteType')=='GFX_apdc_parl_party_button' and int(pos.val('y'))>=335 and abs(int(pos.val('x'))*2+67-1078)<=1)
    check('dismiss_click_is_bound',P+'dismiss_click' in sgui and 'apdc_parl_dismiss_selected = yes' in sgui)
    for name in [P+'candidate_name',P+'candidate_trait',P+'candidate_cost',P+'option_name',P+'option_cost']:
        check(name+'_does_not_swallow_buttons',find(name).val('alwaystransparent')=='yes')
    eco=read('interface/APDC_economy_panel.gui');old={n.val('name'):n for o in parse(eco) for n in o.children}
    replacements={'APDC_eco_law_row':P+'option_row','APDC_eco_law_side':P+'law_side','APDC_eco_law_scroll':P+'option_scroll','APDC_eco_law_list':P+'option_list','APDC_eco_law_button':P+'option_button','APDC_eco_law_current':P+'option_current','APDC_eco_law_icon':P+'option_icon','APDC_eco_law_name':P+'option_name','APDC_eco_law_cost':P+'option_cost','APDC_eco_law_title':P+'side_title','APDC_eco_law_close':P+'side_close','APDC_ECO_LAW_TOOLTIP':P+'law_option_tip','APDC_ECO_LAW_NAME':P+'law_option_name','APDC_ECO_LAW_COST':P+'law_option_cost','APDC_ECO_LAW_TITLE':P+'side_title','APDC_ECO_CLOSE':P+'side_close_tip','GFX_idea_entry_bg_3':'GFX_apdc_parl_law_option_card'}
    for old_name,new_name in [('APDC_eco_law_row',P+'option_row'),('APDC_eco_law_side',P+'law_side')]:
        a=eco[old[old_name].start:old[old_name].end]
        for before,after in sorted(replacements.items(),key=lambda v:-len(v[0])):a=a.replace(before,after)
        b=gui[windows[new_name].start:windows[new_name].end]
        check(new_name+'_matches_economic_source',re.sub(r'\s+','',a)==re.sub(r'\s+','',b))
    overlay=find('APDC_cabinet_pie_overlay')
    check('old_pie_overlay_scale_preserved',overlay.val('scale')=='1.42')
    check('all_nine_party_swatch_boxes',all(find(P+'party_swatch_'+p).val('spriteType')=='GFX_APDC_cabinet_ideology_swatch' for p in PARTIES))
    entry=windows[P+'entry'];check('entry_uses_background_art_origin',entry.get('position').val('y')=='44')
    lectern=find(P+'entry_button');check('lectern_matches_reference_hole',lectern.get('position').val('x')=='98' and lectern.get('position').val('y')=='489')
    from PIL import Image
    with Image.open(ROOT/'gfx/interface/APDC/parliament/entry.png') as image:art_size=image.size
    check('lectern_hitbox_matches_actual_art_size',tuple(int(lectern.get('size').val(k)) for k in ('x','y'))==art_size)
    loc=read('localisation/simp_chinese/apdc_parliament_l_simp_chinese.yml')
    check('chinese_year_month_day',re.search(r'apdc_parl_election_date:0 .*年.*月.*日',loc) is not None)
    props=next(n for o in parse(sgui) for n in o.children if n.key==P+'law_side_ui').get('effects')
    check('both_law_icon_and_row_clicks_bound',props.get(P+'option_icon_click') is not None and props.get(P+'option_button_click') is not None)
    report={'status':'passed','checks':checks,'economic_visual_difference':'only local sprite aliases disable alpha-based hit testing; artwork, frames, dimensions and layout are unchanged'}
    dest=ROOT/'docs/parliament/20261107-ui-corrections/static-ui.json'
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'passed','ui_checks':len(checks)},ensure_ascii=False))


if __name__=='__main__':run()
