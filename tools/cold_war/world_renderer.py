"""Two verified native world layouts; mode changes require rebuilding scripts."""
import json
from common import ROOT,block,setv,iff

def fast_mode():
    return json.loads((ROOT/'tools/cold_war/render_mode.json').read_text('utf-8'))['mode']=='fast'

def build_fast_ui(g,ui,local,scripted,button,icon):
    piece=button('apdc_cw_world_piece',0,0,g['pieces'][0]['world']['image'],tip='APDC_CW_WORLD_COUNTRY')
    piece+=icon('apdc_cw_world_piece_fill',0,0,g['pieces'][0]['world']['image'],'alwaystransparent = yes')
    ui.append(block('containerWindowType','name = "apdc_cw_world_piece_entry" size = { width = 0 height = 0 } clipping = no\n'+piece))
    ui.append(block('containerWindowType','name = "apdc_cw_world_border_entry" size = { width = 0 height = 0 } clipping = no\n'+icon('apdc_cw_world_border',0,0,g['borders'][0]['world']['image'],'alwaystransparent = yes')))
    local['APDC_CW_WORLD_COUNTRY']='§Y[?apdc_cw_world_piece_owners^apdc_cw_world_piece_id.GetName]§!'
    props=''
    for name,frames in [('apdc_cw_world_piece','apdc_cw_world_button_frames'),('apdc_cw_world_piece_fill','apdc_cw_world_fill_frames')]:
        image='apdc_cw_world_fill_images' if name.endswith('_fill') else 'global.apdc_cw_world_piece_images'
        props+=block(name,f'image = "[?{image}^apdc_cw_world_piece_id.GetTokenKey]" x = global.apdc_cw_world_piece_x^apdc_cw_world_piece_id y = global.apdc_cw_world_piece_y^apdc_cw_world_piece_id frame = {frames}^apdc_cw_world_piece_id')
    props+=block('apdc_cw_world_border','image = "[?global.apdc_cw_world_border_images^apdc_cw_world_border_id.GetTokenKey]" x = global.apdc_cw_world_border_x^apdc_cw_world_border_id y = global.apdc_cw_world_border_y^apdc_cw_world_border_id frame = apdc_cw_world_border_frames^apdc_cw_world_border_id')
    trigger=block('apdc_cw_world_piece_click_enabled','OR = { check_variable = { apdc_cw_world_piece_frames^apdc_cw_world_piece_id = 3 } check_variable = { apdc_cw_world_piece_frames^apdc_cw_world_piece_id = 4 } }')
    world=''
    for kind in ['piece','border']:
        world+=block('gridBoxType',f'name = "apdc_cw_world_{kind}_list" position = {{ x = 0 y = 0 }} size = {{ width = 1000 height = 500 }} slotsize = {{ width = 0 height = 0 }} max_slots_horizontal = 1 add_horizontal = no format = "UPPER_LEFT"')
    world+=icon('apdc_cw_coasts',0,0,'GFX_APDC_cw_coasts','alwaystransparent = yes')+icon('apdc_cw_screen_texture',0,0,'GFX_APDC_cw_screen_overlay','alwaystransparent = yes')
    ui.append(block('containerWindowType','name = "apdc_cw_world" position = { x = 38 y = 85 } size = { width = 1000 height = 500 } clipping = yes\n'+world))
    lists=''.join(f'apdc_cw_world_{kind}_list = {{ array = apdc_cw_world_{kind}_rows value = apdc_cw_world_{kind}_id entry_container = "apdc_cw_world_{kind}_entry" }}\n' for kind in ['piece','border'])
    scripted('apdc_cw_world','apdc_cw_world','check_variable = { apdc_cw_detail = 0 }',props,trigger,'apdc_cw_world_piece_click = { apdc_cw_select_world_piece = yes }',lists=lists,parent='apdc_cw_panel',dirty='apdc_cw_map_ui_revision')

def add_fast_data(g,effects):
    init=''
    for kind,entries in [('piece',g['pieces']),('border',g['borders'])]:
        for field in ['images','x','y']:
            init+=f'resize_array = {{ array = global.apdc_cw_world_{kind}_{field} size = {len(entries)} value = 0 }}\n'
        for entry in entries:
            for field,value in [('images','token:'+entry['world']['image']),('x',entry['world']['x']),('y',entry['world']['y'])]:
                init+=setv(f'global.apdc_cw_world_{kind}_{field}^{entry["id"]}',value)
    effects['apdc_cw_ensure_world_draw_lookup']=iff('NOT = { has_global_flag = apdc_cw_world_draw_lookup_v1 }',init+'set_global_flag = apdc_cw_world_draw_lookup_v1')
    frames=f'resize_array = {{ array = apdc_cw_world_button_frames size = {len(g["pieces"])} value = 4 }}\n'
    for entry in g['pieces']:
        i=entry['id'];frames+=setv(f'apdc_cw_world_button_frames^{i}',4)
        frames+=iff(f'OR = {{ check_variable = {{ apdc_cw_world_piece_frames^{i} = 3 }} check_variable = {{ apdc_cw_world_piece_frames^{i} = 4 }} }}',setv(f'apdc_cw_world_button_frames^{i}',1))
    # Literal button construction used frame 4 while disabled. A dynamic image
    # alone retains frame 1, altering edge blending; explicitly retain the state.
    effects['apdc_cw_refresh_world']='apdc_cw_ensure_world_draw_lookup = yes\n'+effects['apdc_cw_refresh_world'].replace('apdc_cw_world_cache_version = 4','apdc_cw_world_cache_version = 5')+frames
    effects['apdc_cw_ensure_world_cache']=effects['apdc_cw_ensure_world_cache'].replace('apdc_cw_world_cache_version = 4','apdc_cw_world_cache_version = 5')
