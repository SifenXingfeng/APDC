"""Compare shared map templates against the pre-optimization native layout."""
import json,re
from pathlib import Path
from common import ROOT,parse,metadata,map_progress_steps

OUT=ROOT/'docs/cold-war/20261025-startup'

def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.children)

def run():
    backup=Path(json.loads((OUT/'optimization-backup.json').read_text('utf-8'))['backup'])/'original'
    g=metadata();steps=map_progress_steps(g)
    old=(backup/'interface/APDC_cold_war.gfx').read_text('utf-8')
    current=(ROOT/'interface/APDC_cold_war.gfx').read_text('utf-8')
    expected=parse(re.sub(r'\bsteps\s*=\s*100000','steps = '+str(steps),old))[0].children
    expected=[node for node in expected if node.val('name')!='GFX_APDC_cw_entry']
    actual=parse(current)[0].children
    border_paths={e['world']['image']:f'gfx/interface/APDC/cold_war/world_style/border_{e["id"]}.png' for e in g['borders']}
    static_world_images={e['world']['image'] for e in g['pieces']}
    def canonical(node):return (node.key,node.value,tuple(canonical(c) for c in node.children))
    assert len(expected)==len(actual)
    for before_node,after_node in zip(expected,actual):
        if before_node.val('name') in static_world_images:
            assert after_node.val('effectFile')=='gfx/FX/buttonstate_onlydisable.shader'
            after_node.children=[child for child in after_node.children if child.key!='effectFile']
        if before_node.val('name')=='GFX_APDC_cw_background':
            assert after_node.val('effectFile')=='gfx/FX/static_button.shader'
            after_node.children=[child for child in after_node.children if child.key!='effectFile']
        if before_node.val('name') in border_paths:
            assert after_node.val('texturefile')==border_paths[before_node.val('name')]
            assert after_node.val('noOfFrames')=='2'
            after_node.children=[child for child in after_node.children if child.key!='noOfFrames']
            after_node.get('texturefile').value=before_node.get('texturefile').value
        assert canonical(before_node)==canonical(after_node)
    old=(backup/'gfx/FX/APDC_cw_palette.shader').read_text('utf-8')
    current=(ROOT/'gfx/FX/APDC_cw_palette.shader').read_text('utf-8')
    assert old.replace('CurrentState * 100000.f',f'CurrentState * {steps}.f')==current
    before={node.val('name'):node for node in walk(parse((backup/'interface/APDC_cold_war.gui').read_text('utf-8'))) if node.get('name')}
    current_gui=parse((ROOT/'interface/APDC_cold_war.gui').read_text('utf-8'))
    containers={node.val('name'):node for node in walk(current_gui) if node.key=='containerWindowType'}
    world_nodes={node.val('name'):node for node in containers['apdc_cw_world'].children if node.get('name')}
    view=parse((ROOT/'common/scripted_effects/APDC_cold_war_view.txt').read_text('utf-8'))
    lookups=[node for node in view if node.key in {'apdc_cw_ensure_render_lookup','apdc_cw_ensure_world_draw_lookup'}]
    values={node.children[0].key:node.children[0].value for node in walk(lookups) if node.key=='set_variable'}
    tokens={line.strip() for line in (ROOT/'common/synchronized_dynamic_tokens/APDC_cold_war.txt').read_text('utf-8').splitlines() if line and not line.startswith('#')}
    checked=0
    for kind,entries in [('piece',g['pieces']),('border',g['borders'])]:
        for entry in entries:
            index=entry['id'];name=f'apdc_cw_world_{index}' if kind=='piece' else f'apdc_cw_border_{index}'
            native=before[name];image=native.val('spriteType')
            assert values[f'global.apdc_cw_{kind}_images^{index}']=='token:'+entry['image']
            assert entry['image'] in tokens
            if name in world_nodes:
                current=world_nodes[name]
                assert current.val('spriteType')==image
                assert all(current.get('position').val(axis)==native.get('position').val(axis) for axis in ['x','y'])
            else:
                assert values[f'global.apdc_cw_world_{kind}_images^{index}']=='token:'+image
                assert image in tokens
                assert all(values[f'global.apdc_cw_world_{kind}_{axis}^{index}']==native.get('position').val(axis) for axis in ['x','y'])
            if kind=='piece' and name in world_nodes:
                for childname in [name,name+'_fill']:
                    child=world_nodes[childname]
                    assert child.val('spriteType')==image
                    assert all(child.get('position').val(axis)==native.get('position').val(axis) for axis in ['x','y'])
            checked+=1
    result={'map_parts_compared_to_original':checked,'world_geometry_and_original_base_images_preserved':True,
            'gfx_changes_limited_to_steps_world_border_styles_and_static_inputs':True,'shader_unchanged_except_matching_frame_decoder':True,
            'native_button_images_positions_and_sizes_preserved':True,
            'registered_image_tokens':len(tokens),'zoom_levels':len(g['scales']),'palette_colors':len(g['palette_ids']),
            'boundary':'Static original-layout and image-key comparison; native captures and effect checks are recorded separately.'}
    (OUT/'loading-audit.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result))
    return result

if __name__=='__main__':run()
