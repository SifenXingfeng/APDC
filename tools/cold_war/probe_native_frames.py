"""Isolated native-button frame probe; never changes the production GUI."""
import json,sys
from common import ROOT,parse,block,setv,iff,metadata
import qa

def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)

def prepare():
    sys.argv.append('--world-review');profile=qa.prepare();g=metadata();driver=profile/'driver'
    base='gfx/interface/APDC/cold_war/'
    def icon(name,sprite,extra=''):
        return block('iconType',f'name = "{name}" position = {{ x = 0 y = 0 }} spriteType = "{sprite}" '+extra)
    entry=block('buttonType',f'name = "apdc_cw_probe_piece" position = {{ x = 0 y = 0 }} spriteType = "{g["pieces"][0]["world"]["image"]}" pdx_tooltip = "APDC_CW_PROBE_COUNTRY" clicksound = click_default')
    entry+=icon('apdc_cw_probe_fill',g['pieces'][0]['world']['image'],'alwaystransparent = yes')
    templates=block('containerWindowType','name = "apdc_cw_probe_piece_entry" size = { width = 0 height = 0 } clipping = no\n'+entry)
    templates+=block('containerWindowType','name = "apdc_cw_probe_border_entry" size = { width = 0 height = 0 } clipping = no\n'+icon('apdc_cw_probe_border',g['borders'][0]['world']['image'],'alwaystransparent = yes'))
    world=''
    for kind in ['piece','border']:
        world+=block('gridBoxType',f'name = "apdc_cw_probe_{kind}_list" position = {{ x = 0 y = 0 }} size = {{ width = 1000 height = 500 }} slotsize = {{ width = 0 height = 0 }} max_slots_horizontal = 1 add_horizontal = no format = "UPPER_LEFT"')
    world+=icon('apdc_cw_coasts','GFX_APDC_cw_coasts','alwaystransparent = yes')+icon('apdc_cw_screen_texture','GFX_APDC_cw_screen_overlay','alwaystransparent = yes')
    replacement=block('containerWindowType','name = "apdc_cw_world" position = { x = 38 y = 85 } size = { width = 1000 height = 500 } clipping = yes\n'+world)
    rel='interface/APDC_cold_war.gui';text=(ROOT/rel).read_text('utf-8');node=next(n for n in walk(parse(text)) if n.val('name')=='apdc_cw_world')
    text=text[:node.start]+replacement+text[node.end:];i=text.rfind('}');text=text[:i]+templates+text[i:]
    p=driver/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,'utf-8')
    props=''
    for name,frame in [('apdc_cw_probe_piece','apdc_cw_probe_button_frame'),('apdc_cw_probe_fill','apdc_cw_world_piece_frames')]:
        props+=block(name,f'image = "[?global.apdc_cw_probe_piece_images^apdc_cw_world_piece_id.GetTokenKey]" x = global.apdc_cw_probe_piece_x^apdc_cw_world_piece_id y = global.apdc_cw_probe_piece_y^apdc_cw_world_piece_id frame = {frame}^apdc_cw_world_piece_id')
    props+=block('apdc_cw_probe_border','image = "[?global.apdc_cw_probe_border_images^apdc_cw_world_border_id.GetTokenKey]" x = global.apdc_cw_probe_border_x^apdc_cw_world_border_id y = global.apdc_cw_probe_border_y^apdc_cw_world_border_id')
    trigger=block('apdc_cw_probe_piece_click_enabled','OR = { check_variable = { apdc_cw_world_piece_frames^apdc_cw_world_piece_id = 3 } check_variable = { apdc_cw_world_piece_frames^apdc_cw_world_piece_id = 4 } }')
    lists=''.join(f'apdc_cw_probe_{kind}_list = {{ array = apdc_cw_world_{kind}_rows value = apdc_cw_world_{kind}_id entry_container = "apdc_cw_probe_{kind}_entry" }}\n' for kind in ['piece','border'])
    replacement=block('apdc_cw_world','context_type = player_context\nwindow_name = "apdc_cw_world"\nparent_scripted_gui = apdc_cw_panel\nvisible = { check_variable = { apdc_cw_detail = 0 } }\ndirty = apdc_cw_map_ui_revision\n'+block('properties',props)+block('triggers',trigger)+block('effects','apdc_cw_probe_piece_click = { apdc_cw_select_world_piece = yes }')+block('dynamic_lists',lists))
    rel='common/scripted_guis/APDC_cold_war.txt';text=(ROOT/rel).read_text('utf-8');node=next(n for n in walk(parse(text)) if n.key=='apdc_cw_world');(driver/rel).parent.mkdir(parents=True,exist_ok=True);(driver/rel).write_text(text[:node.start]+replacement+text[node.end:],'utf-8')
    init=''
    for kind,entries in [('piece',g['pieces']),('border',g['borders'])]:
        for field in ['images','x','y']:init+=f'resize_array = {{ array = global.apdc_cw_probe_{kind}_{field} size = {len(entries)} value = 0 }}\n'
        for entry in entries:
            for field,value in [('images','token:'+entry['world']['image']),('x',entry['world']['x']),('y',entry['world']['y'])]:init+=setv(f'global.apdc_cw_probe_{kind}_{field}^{entry["id"]}',value)
    frames=f'resize_array = {{ array = apdc_cw_probe_button_frame size = {len(g["pieces"])} value = 4 }}\n'
    for entry in g['pieces']:
        i=entry['id'];frames+=setv(f'apdc_cw_probe_button_frame^{i}',4)+iff(f'OR = {{ check_variable = {{ apdc_cw_world_piece_frames^{i} = 3 }} check_variable = {{ apdc_cw_world_piece_frames^{i} = 4 }} }}',setv(f'apdc_cw_probe_button_frame^{i}',1))
    (driver/'common/scripted_effects/APDC_frame_probe.txt').write_text(block('apdc_cw_probe_init',init)+block('apdc_cw_probe_frames',frames),'utf-8')
    (driver/'common/on_actions/zzzz_APDC_frame_probe.txt').write_text('on_actions = { on_startup = { effect = { GER = { apdc_cw_probe_init = yes apdc_cw_probe_frames = yes } } } }','utf-8')
    p=driver/'common/scripted_effects/APDC_cold_war_qa.txt';text=p.read_text('utf-8');p.write_text(text.replace('log = "APDC_CW_QA COMPLETE"','apdc_cw_probe_frames = yes\nlog = "APDC_CW_QA COMPLETE"'),'utf-8')
    p=driver/'common/synchronized_dynamic_tokens/APDC_frame_probe.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(e['world']['image'] for e in g['pieces']+g['borders'])+'\n','utf-8')
    p=driver/'localisation/simp_chinese/APDC_frame_probe_l_simp_chinese.yml';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('l_simp_chinese:\n APDC_CW_PROBE_COUNTRY:0 "§Y[?apdc_cw_world_piece_owners^apdc_cw_world_piece_id.GetName]§!"\n','utf-8-sig')
    (ROOT/'docs/cold-war/20261025-startup/native-frame-probe-profile.txt').write_text(str(profile),'utf-8')
    print(json.dumps({'isolated_native_frame_probe':str(profile)}));return profile

if __name__=='__main__':prepare()
