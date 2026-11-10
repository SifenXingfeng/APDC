"""Generate geometry initialization, per-player view caches and dynamic localisation."""
import math,json
from world_renderer import fast_mode,add_fast_data
from common import ROOT, GAME, parse, block, iff, setv, add, write, metadata
from build_backend import AXES
from world_style import black_sprite,UNINHABITED

def build():
    g=metadata();states={int(k):v for k,v in g['states'].items()};effects={};loc={};defined=[]
    def dt(name,clauses):
        defined.append(block('defined_text','name = '+name+'\n'+''.join('text = { '+('trigger = { '+test+' } ' if test else '')+'localization_key = '+key+' }\n' for test,key in clauses)))
    tagfiles={p.name:p for p in (GAME/'common/country_tags').glob('*.txt')}
    tagfiles.update({p.name:p for p in (ROOT/'common/country_tags').glob('*.txt')})
    valid_tags={n.key for p in tagfiles.values() for n in parse(p.read_text('utf-8-sig')) if n.value}
    init=''
    for sid,s in states.items():
        init+=block(str(sid),''.join(setv('apdc_cw_'+k,s[k]) for k in ('x0','x1','y0','y1','shift_x0','shift_x1')))
    # Cosmetic identity colours override registered country defaults without changing game colours.
    for tag,idx in g['palette_ids'].items():
        if tag in valid_tags:init+=block(tag,setv('apdc_cw_palette',idx))
    init+='every_country = { if = { limit = { NOT = { has_variable = apdc_cw_palette } } set_variable = { apdc_cw_palette = 1 } } }\n'
    effects['apdc_cw_initialize_geometry']=init
    tokens=[entry['image'] for entry in g['pieces']+g['borders']]
    tokens += [name for entry in g['pieces'] for name in [entry['world']['image'],black_sprite(entry['id'])]]
    if fast_mode():tokens += [entry['world']['image'] for entry in g['pieces']+g['borders']]
    write('common/synchronized_dynamic_tokens/APDC_cold_war.txt','# Constant image keys for the shared Cold War map templates.\n'+'\n'.join(dict.fromkeys(tokens)))
    render=''
    for kind,entries in [('piece',g['pieces']),('border',g['borders'])]:
        render+=f'resize_array = {{ array = global.apdc_cw_{kind}_images size = {len(entries)} value = 0 }}\n'
        for entry in entries:
            render+=setv(f'global.apdc_cw_{kind}_images^{entry["id"]}','token:'+entry['image'])
    effects['apdc_cw_ensure_render_lookup']=iff('NOT = { has_global_flag = apdc_cw_render_lookup_v2 }',render+'set_global_flag = apdc_cw_render_lookup_v2')
    style=f'resize_array = {{ array = global.apdc_cw_world_normal_images size = {len(g["pieces"])} value = 0 }}\nresize_array = {{ array = global.apdc_cw_world_black_images size = {len(g["pieces"])} value = 0 }}\n'
    for entry in g['pieces']:
        style+=setv(f'global.apdc_cw_world_normal_images^{entry["id"]}','token:'+entry['world']['image'])+setv(f'global.apdc_cw_world_black_images^{entry["id"]}','token:'+black_sprite(entry['id']))
    effects['apdc_cw_ensure_world_style_lookup']=iff('NOT = { has_global_flag = apdc_cw_world_style_lookup_v1 }',style+'set_global_flag = apdc_cw_world_style_lookup_v1')
    refresh='apdc_cw_ensure_render_lookup = yes\napdc_cw_ensure_world_style_lookup = yes\nset_variable = { global.apdc_cw_viewer = THIS }\n'+f'resize_array = {{ array = apdc_cw_world_frames size = {max(states)+1} value = 2 }}\nresize_array = {{ array = apdc_cw_world_state_owners size = {max(states)+1} value = 0 }}\n'
    for sid in states:
        refresh+=block(str(sid),block('owner','set_variable = { global.apdc_cw_map_owner = THIS }'))
        refresh+=setv(f'apdc_cw_world_state_owners^{sid}','global.apdc_cw_map_owner')
        refresh+=setv('apdc_cw_world_frames^'+str(sid),2)
        refresh+=iff('is_in_array = { array = apdc_cw_intervenable value = var:global.apdc_cw_map_owner }',setv(f'apdc_cw_world_frames^{sid}',3))
        refresh+=iff('is_in_array = { array = apdc_cw_controlled value = var:global.apdc_cw_map_owner }',setv(f'apdc_cw_world_frames^{sid}',4))
        refresh+=iff('var:global.apdc_cw_map_owner = { tag = PREV }',setv(f'apdc_cw_world_frames^{sid}',1))
    refresh+='clear_array = apdc_cw_world_piece_rows\nclear_array = apdc_cw_world_border_rows\n'
    refresh+=f'resize_array = {{ array = apdc_cw_world_piece_owners size = {len(g["pieces"])} value = 0 }}\nresize_array = {{ array = apdc_cw_world_piece_frames size = {len(g["pieces"])} value = 2 }}\n'
    refresh+=f'resize_array = {{ array = apdc_cw_world_fill_images size = {len(g["pieces"])} value = 0 }}\nresize_array = {{ array = apdc_cw_world_fill_frames size = {len(g["pieces"])} value = 1 }}\n'
    for entry in g['pieces']:
        i=entry['id'];sid=entry['state']
        refresh+=setv(f'apdc_cw_world_piece_owners^{i}',f'apdc_cw_world_state_owners^{sid}')+setv(f'apdc_cw_world_piece_frames^{i}',f'apdc_cw_world_frames^{sid}')+f'add_to_array = {{ array = apdc_cw_world_piece_rows value = {i} }}\n'
        refresh+=setv(f'apdc_cw_world_fill_images^{i}',f'global.apdc_cw_world_normal_images^{i}')+setv(f'apdc_cw_world_fill_frames^{i}',f'apdc_cw_world_frames^{sid}')
        refresh+=iff(f'var:apdc_cw_world_piece_owners^{i} = {{ tag = {UNINHABITED} }}',setv(f'apdc_cw_world_fill_images^{i}',f'global.apdc_cw_world_black_images^{i}')+setv(f'apdc_cw_world_fill_frames^{i}',1))
    refresh+=f'clear_array = apdc_cw_world_border_visible\nresize_array = {{ array = apdc_cw_world_border_visible size = {len(g["borders"])} value = 0 }}\nclear_array = apdc_cw_world_border_frames\nresize_array = {{ array = apdc_cw_world_border_frames size = {len(g["borders"])} value = 1 }}\n'
    for entry in g['borders']:
        refresh+=iff(f'NOT = {{ {entry["a"]} = {{ owner = {{ {entry["b"]} = {{ is_owned_by = PREV }} }} }} }}',setv(f'apdc_cw_world_border_visible^{entry["id"]}',1)+f'add_to_array = {{ array = apdc_cw_world_border_rows value = {entry["id"]} }}')
        refresh+=iff(f'OR = {{ {entry["a"]} = {{ is_owned_by = {UNINHABITED} }} {entry["b"]} = {{ is_owned_by = {UNINHABITED} }} }}',setv(f'apdc_cw_world_border_frames^{entry["id"]}',2))
    refresh+=setv('apdc_cw_seen_map_revision','global.apdc_cw_map_revision')+setv('apdc_cw_world_cache_version',4)+add('apdc_cw_world_cache_builds',1)+add('apdc_cw_map_ui_revision',1)
    effects['apdc_cw_refresh_world']=refresh
    effects['apdc_cw_ensure_world_cache']=iff('OR = { NOT = { check_variable = { apdc_cw_world_cache_version = 4 } } NOT = { check_variable = { apdc_cw_seen_map_revision = global.apdc_cw_map_revision } } }','apdc_cw_refresh_world = yes')
    # Dirty data can be consumed while a parent GUI is hidden. Showing the
    # window must rebind its frames/triggers even when the cached data is valid.
    effects['apdc_cw_bind_world_ui']='apdc_cw_ensure_world_cache = yes\n'+add('apdc_cw_map_ui_revision',1)
    effects['apdc_cw_select_world_piece']=setv('apdc_cw_selected','apdc_cw_world_piece_owners^apdc_cw_world_piece_id')+setv('apdc_cw_detail',1)+'apdc_cw_prepare_detail = yes\napdc_cw_refresh_view = yes\n'
    effects['apdc_cw_check_core_map']=f'''resize_array = {{ array = apdc_cw_core_mask size = {max(states)+1} value = 0 }}
set_variable = {{ global.apdc_cw_core_changed = 0 }}
set_variable = {{ apdc_cw_owned_core_count = 0 }}
every_owned_state = {{
set_variable = {{ global.apdc_cw_core_state = THIS }}
set_variable = {{ global.apdc_cw_core_expected = 0 }}
if = {{ limit = {{ is_core_of = PREV }} set_variable = {{ global.apdc_cw_core_expected = 1 }} PREV = {{ add_to_variable = {{ apdc_cw_owned_core_count = 1 }} }} }}
PREV = {{
if = {{ limit = {{ NOT = {{ check_variable = {{ apdc_cw_core_mask^global.apdc_cw_core_state = global.apdc_cw_core_expected }} }} }}
set_variable = {{ global.apdc_cw_core_changed = 1 }}
set_variable = {{ apdc_cw_core_mask^global.apdc_cw_core_state = global.apdc_cw_core_expected }}
}} }} }}
if = {{ limit = {{ check_variable = {{ global.apdc_cw_core_changed = 1 }} }} add_to_variable = {{ apdc_cw_core_revision = 1 }} }}
'''
    bbox='apdc_cw_ensure = yes\napdc_cw_check_core_map = yes\n'+setv('apdc_cw_min_x',5120)+setv('apdc_cw_max_x',0)+setv('apdc_cw_min_shift_x',5120)+setv('apdc_cw_max_shift_x',0)+setv('apdc_cw_min_y',2560)+setv('apdc_cw_max_y',0)
    bbox+=setv('apdc_cw_detail_state_count',0)+'every_owned_state = { limit = { is_core_of = PREV }\nPREV = { add_to_variable = { apdc_cw_detail_state_count = 1 } }\n'
    for field,statefield,op in [('min_x','x0','<'),('max_x','x1','>'),('min_shift_x','shift_x0','<'),('max_shift_x','shift_x1','>'),('min_y','y0','<'),('max_y','y1','>')]:
        bbox+=iff(f'check_variable = {{ apdc_cw_{statefield} {op} PREV.apdc_cw_{field} }}',block('PREV',setv('apdc_cw_'+field,'PREV.apdc_cw_'+statefield)))
    bbox+='}\n'+iff('check_variable = { apdc_cw_detail_state_count = 0 }',''.join(setv('apdc_cw_'+field,0) for field in ['min_x','max_x','min_shift_x','max_shift_x','min_y','max_y']))+setv('apdc_cw_span','apdc_cw_max_x')+'subtract_from_variable = { apdc_cw_span = apdc_cw_min_x }\n'
    bbox+=setv('apdc_cw_shift_span','apdc_cw_max_shift_x')+'subtract_from_variable = { apdc_cw_shift_span = apdc_cw_min_shift_x }\n'
    bbox+=setv('apdc_cw_origin',0)+iff('check_variable = { apdc_cw_shift_span < apdc_cw_span }',setv('apdc_cw_origin',1)+setv('apdc_cw_span','apdc_cw_shift_span')+setv('apdc_cw_min_x','apdc_cw_min_shift_x'))
    bbox+=setv('apdc_cw_height','apdc_cw_max_y')+'subtract_from_variable = { apdc_cw_height = apdc_cw_min_y }\n'+setv('apdc_cw_zoom',0)
    for z,s in enumerate(g['scales']):
        bbox+=iff(f'check_variable = {{ apdc_cw_detail_state_count > 0 }} check_variable = {{ apdc_cw_span < {460/s+0.0001:.5f} }} check_variable = {{ apdc_cw_height < {430/s+0.0001:.5f} }}',setv('apdc_cw_zoom',z)+setv('apdc_cw_scale',f'{s:.5f}'))
    effects['apdc_cw_compute_bounds']=bbox
    prep='''set_variable = { global.apdc_cw_viewer = THIS }
var:apdc_cw_selected = { apdc_cw_compute_bounds = yes }
set_variable = { apdc_cw_detail_zoom = var:apdc_cw_selected.apdc_cw_zoom }
set_variable = { apdc_cw_detail_origin = var:apdc_cw_selected.apdc_cw_origin }
clear_array = apdc_cw_detail_pieces
clear_array = apdc_cw_detail_borders
'''
    # Scope fields use an explicit copy through the target scope, avoiding dotted variable targets.
    prep='set_variable = { global.apdc_cw_viewer = THIS }\nvar:apdc_cw_selected = { apdc_cw_compute_bounds = yes\n'+block('var:global.apdc_cw_viewer',setv('apdc_cw_detail_state_count','PREV.apdc_cw_detail_state_count')+setv('apdc_cw_detail_zoom','PREV.apdc_cw_zoom')+setv('apdc_cw_detail_origin','PREV.apdc_cw_origin')+setv('apdc_cw_detail_min_x','PREV.apdc_cw_min_x')+setv('apdc_cw_detail_min_y','PREV.apdc_cw_min_y')+setv('apdc_cw_detail_span','PREV.apdc_cw_span')+setv('apdc_cw_detail_height','PREV.apdc_cw_height'))+'}\nclear_array = apdc_cw_detail_pieces\nclear_array = apdc_cw_detail_borders\n'
    # Build only the selected state's pieces; coordinates are rebased before
    # multiplication so microstates never overflow the engine fixed-point range.
    prep+=setv('apdc_cw_detail_scale', '0.0625')
    for z,scale in enumerate(g['scales']):
        prep+=iff(f'check_variable = {{ apdc_cw_detail_zoom = {z} }}',setv('apdc_cw_detail_scale',f'{scale:.5f}'))
    prep+=setv('apdc_cw_offset_x','apdc_cw_detail_span')+'multiply_variable = { apdc_cw_offset_x = apdc_cw_detail_scale }\nmultiply_variable = { apdc_cw_offset_x = -0.5 }\n'+add('apdc_cw_offset_x',250)
    prep+=setv('apdc_cw_offset_y','apdc_cw_detail_height')+'multiply_variable = { apdc_cw_offset_y = apdc_cw_detail_scale }\nmultiply_variable = { apdc_cw_offset_y = -0.5 }\n'+add('apdc_cw_offset_y',260)
    prep+=setv('apdc_cw_native_offset_x','apdc_cw_offset_x')+'divide_variable = { apdc_cw_native_offset_x = apdc_cw_detail_scale }\n'+setv('apdc_cw_native_offset_y','apdc_cw_offset_y')+'divide_variable = { apdc_cw_native_offset_y = apdc_cw_detail_scale }\n'
    for kind,entries in [('pieces',g['pieces']),('borders',g['borders'])]:
        prep+=f'resize_array = {{ array = apdc_cw_{kind}_x size = {len(entries)} value = 0 }}\nresize_array = {{ array = apdc_cw_{kind}_y size = {len(entries)} value = 0 }}\n'
        for e in entries:
            i=e['id']
            def eligible(sid):return f'{sid} = {{ is_owned_by = var:global.apdc_cw_detail_target is_core_of = var:global.apdc_cw_detail_target }}'
            cond=eligible(e['state']) if kind=='pieces' else f'OR = {{ AND = {{ {eligible(e["a"])} NOT = {{ {eligible(e["b"])} }} }} AND = {{ {eligible(e["b"])} NOT = {{ {eligible(e["a"])} }} }} }}'
            b=f'add_to_array = {{ array = apdc_cw_detail_{kind} value = {i} }}\n'+setv(f'apdc_cw_{kind}_x^{i}',e['x'])
            b+=iff('check_variable = { apdc_cw_detail_origin = 1 }',setv(f'apdc_cw_{kind}_x^{i}',(e['x']+2560)%5120))
            b+=f'subtract_from_variable = {{ apdc_cw_{kind}_x^{i} = apdc_cw_detail_min_x }}\nsubtract_from_variable = {{ apdc_cw_{kind}_x^{i} = 64 }}\n'+setv(f'apdc_cw_{kind}_y^{i}',e['y'])+f'subtract_from_variable = {{ apdc_cw_{kind}_y^{i} = apdc_cw_detail_min_y }}\nsubtract_from_variable = {{ apdc_cw_{kind}_y^{i} = 64 }}\n'
            b+=add(f'apdc_cw_{kind}_x^{i}','apdc_cw_native_offset_x')+add(f'apdc_cw_{kind}_y^{i}','apdc_cw_native_offset_y')
            prep+=iff(cond,b)
    prep='apdc_cw_ensure_render_lookup = yes\nset_variable = { global.apdc_cw_detail_target = apdc_cw_selected }\n'+prep+add('apdc_cw_detail_ui_revision',1)
    prep+='var:apdc_cw_selected = { set_variable = { global.apdc_cw_current_core_revision = apdc_cw_core_revision } }\n'+setv('apdc_cw_seen_core_revision','global.apdc_cw_current_core_revision')
    effects['apdc_cw_prepare_detail']=prep
    # Refreshing native action metadata is author-owned gameplay. Geography
    # rebuilds must not replace this with generated per-action lists.
    native=(ROOT/'common/scripted_effects/APDC_cold_war_view.txt').read_text('utf-8-sig')
    node=next(n for n in parse(native) if n.key=='apdc_cw_refresh_view')
    effects[node.key]=native[node.value_start+1:node.value_end-1]

    pie='resize_array = { array = apdc_cw_pie_source size = 360 value = 0 }\nresize_array = { array = apdc_cw_pie_color size = 360 value = 1 }\nresize_array = { array = apdc_cw_pie_group size = 360 value = 0 }\nset_temp_variable = { apdc_cw_pie_end = 0 }\nset_temp_variable = { apdc_cw_pie_sum = 0 }\n'
    pie+='for_each_loop = { array = apdc_cw_ui_shares value = apdc_cw_pie_share index = apdc_cw_pie_idx\nadd_to_temp_variable = { apdc_cw_pie_sum = apdc_cw_pie_share }\nset_temp_variable = { apdc_cw_pie_cutoff = apdc_cw_pie_sum }\nmultiply_temp_variable = { apdc_cw_pie_cutoff = 3.6 }\nround_temp_variable = apdc_cw_pie_cutoff\nclamp_temp_variable = { var = apdc_cw_pie_cutoff min = 0 max = 360 }\nset_temp_variable = { apdc_cw_color_index = apdc_cw_ui_palette^apdc_cw_pie_idx }\nsubtract_from_temp_variable = { apdc_cw_color_index = 1 }\nset_temp_variable = { apdc_cw_color_group = apdc_cw_color_index }\nmodulo_temp_variable = { apdc_cw_color_index = 32 }\nsubtract_from_temp_variable = { apdc_cw_color_group = apdc_cw_color_index }\ndivide_temp_variable = { apdc_cw_color_group = 32 }\nadd_to_temp_variable = { apdc_cw_color_index = 1 }\nfor_loop_effect = { start = apdc_cw_pie_end end = apdc_cw_pie_cutoff value = apdc_cw_slice\nset_variable = { apdc_cw_pie_source^apdc_cw_slice = apdc_cw_pie_idx }\nset_variable = { apdc_cw_pie_color^apdc_cw_slice = apdc_cw_color_index }\nset_variable = { apdc_cw_pie_group^apdc_cw_slice = apdc_cw_color_group }\n}\nset_temp_variable = { apdc_cw_pie_end = apdc_cw_pie_cutoff }\n}\n'
    effects['apdc_cw_rebuild_pie']=pie
    groups=math.ceil(len(g['palette_ids'])/32)
    # Keep the same 360 native hit regions/rotations. Cache values in arrays and
    # bind the hovered index in scripted localisation, instead of compiling
    # 360 copies of every possible law/source/name tooltip.
    for typ in ['owner','shares','net','law','auto','competition']:
        effects['apdc_cw_rebuild_pie']+=f'resize_array = {{ array = apdc_cw_pie_{typ} size = 360 value = 0 }}\n'
    effects['apdc_cw_rebuild_pie']+='for_loop_effect = { start = 0 end = 360 value = apdc_cw_copy_slice\n'
    effects['apdc_cw_rebuild_pie']+=setv('apdc_cw_copy_index','apdc_cw_pie_source^apdc_cw_copy_slice')+setv('apdc_cw_pie_owner^apdc_cw_copy_slice','apdc_cw_ui_sources^apdc_cw_copy_index')
    for typ in ['shares','net','law','auto','competition']:
        effects['apdc_cw_rebuild_pie']+=setv(f'apdc_cw_pie_{typ}^apdc_cw_copy_slice',f'apdc_cw_ui_{typ}^apdc_cw_copy_index')
    effects['apdc_cw_rebuild_pie']+='}\n'
    for i in range(360):
        dt('APDCCWPieImage'+str(i),[(f'check_variable = {{ apdc_cw_pie_group^{i} = {n} }}',f'GFX_APDC_cw_pie_{n}') for n in range(groups)])
        loc[f'APDC_CW_PIE_{i}']=f'[APDCCWPieBind{i}]'
        dt('APDCCWPieBind'+str(i),[(f'set_temp_variable = {{ apdc_cw_tooltip_slice = {i} }} set_temp_variable = {{ apdc_na_source_cursor = 0 }} set_temp_variable = {{ apdc_na_hover_actor = apdc_cw_pie_owner^apdc_cw_tooltip_slice }} always = yes','APDC_CW_PIE_GENERIC')])
    owner='apdc_cw_pie_owner^apdc_cw_tooltip_slice'
    dt('APDCCWPieName',[(f'var:{owner} = {{ tag = var:PREV.apdc_cw_selected }}','APDC_CW_AUTONOMY')]+[(f'var:{owner} = {{ tag = {tag} }}','APDC_CW_SHORT_'+tag) for tag in ['GER','FRA','LLU','SOV']]+[('','APDC_CW_PIE_NAME')])
    loc['APDC_CW_PIE_NAME']=f'[?{owner}.GetName]'
    for typ,label in [('net',''),('auto','经济与军事影响'),('competition','其他份额等比调整')]:
        clauses=[];v=f'apdc_cw_pie_{typ}^apdc_cw_tooltip_slice'
        for sign,op,color,prefix in [('P','>','G','+'),('N','<','R','')]:
            key=f'APDC_CW_PIE_{typ}_{sign}'
            loc[key]=('' if typ=='net' else '\n'+label+'：')+f'§{color}{prefix}[?{v}|2]§!'+(' 个百分点' if typ!='net' else '')
            clauses.append((f'check_variable = {{ {v} {op} 0 }}',key))
        if typ=='net':
            loc['APDC_CW_PIE_ZERO']='§W0.00§!';clauses.append(('','APDC_CW_PIE_ZERO'))
        else:clauses.append(('','APDC_CW_EMPTY'))
        dt('APDCCW'+typ.capitalize(),clauses)
    # Dynamic source localization iterates runtime contribution records.
    native_loc=(ROOT/'common/scripted_localisation/APDC_cold_war_view.txt').read_text('utf-8-sig')
    for node in parse(native_loc):
        if node.val('name') in ('APDCNativeCWSourceLines','APDCNativeCWSourceName'):
            defined.append(native_loc[node.start:node.end])
    loc['APDC_CW_PIE_GENERIC']='§Y[APDCCWPieName]§!\n§W[?apdc_cw_pie_shares^apdc_cw_tooltip_slice|2]%§!\n每日变化：[APDCCWNet][APDCNativeCWSourceLines][APDCCWAuto][APDCCWCompetition]'
    loc['APDC_CW_SHORT_SOV']='苏联'
    if fast_mode():add_fast_data(g,effects)
    write('common/scripted_effects/APDC_cold_war_view.txt',''.join(block(k,v) for k,v in effects.items()))
    # Build will merge these with interface localisation.
    (ROOT/'docs/cold-war/20261024/view-localisation.json').write_text(json.dumps(loc,ensure_ascii=False),'utf-8')
    write('common/scripted_localisation/APDC_cold_war_view.txt',''.join(defined))

if __name__=='__main__':build()
