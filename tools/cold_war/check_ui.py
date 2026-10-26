"""Audit native sprite input extents, tab stacking and solid sector geometry."""
import json, math
from PIL import Image
from common import ROOT, OUT, parse

def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.children)

def run():
    nodes=list(walk(parse((ROOT/'interface/APDC_cold_war.gui').read_text('utf-8'))))
    named={n.val('name').strip('"'):n for n in nodes if n.get('name')}
    sprites={}
    for filename in ['APDC_cold_war.gfx','APDC_cold_war_hit.gfx','APDC_button_feedback.gfx','APDC_custom_panel_exit.gfx']:
        for n in walk(parse((ROOT/'interface'/filename).read_text('utf-8'))):
            if n.get('name') and n.get('texturefile'):
                sprites[n.val('name').strip('"')]=n
    extents=[]
    for name in ['apdc_cw_tab_1','apdc_cw_tab_2','apdc_cw_tab_3','apdc_cw_law_execute','apdc_cw_law_stop','apdc_cw_close','apdc_cw_legend_hit']:
        n=named[name];s=sprites[n.val('spriteType').strip('"')];texture=ROOT/s.val('texturefile').strip('"')
        width,height=Image.open(texture).size;frames=int(s.val('noOfFrames') or 1)
        expected=(int(n.get('size').val('x')),int(n.get('size').val('y')))
        assert (width//frames,height)==expected,(name,texture,(width//frames,height),expected)
        assert texture.name!='empty.png',name
        extents.append({'button':name,'texture':texture.relative_to(ROOT).as_posix(),'native_input_size':expected})
    children=named['apdc_cw_controls'].children
    order={n.val('name').strip('"'):i for i,n in enumerate(children) if n.get('name')}
    background=order['apdc_cw_control_background']
    sg=(ROOT/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8')
    for i in range(1,4):
        assert order[f'apdc_cw_tab_{i}']<background<order[f'apdc_cw_tab_{i}_active']<order[f'apdc_cw_tab_{i}_label']
        assert named[f'apdc_cw_tab_{i}_active'].val('alwaystransparent')=='yes'
        assert f'apdc_cw_tab_{i}_active_visible = {{\ncheck_variable = {{ apdc_cw_tab = {i} }}' in sg
        assert f'apdc_cw_tab_{i}_click = {{' in sg
    costs=[n.val('name').strip('"') for n in named['apdc_cw_law_entry'].children if n.get('name') and 'cost' in n.val('name')]
    assert costs==['apdc_cw_law_cost'],costs
    laws=json.loads((ROOT/'tools/cold_war/laws.json').read_text('utf-8'))
    assert all('cost' in law and 'execute_cost' not in law and 'stop_cost' not in law for law in laws)
    body=(ROOT/'common/scripted_effects/APDC_cold_war.txt').read_text('utf-8')
    assert 'apdc_cw_law_stop_cost' not in body
    alpha=Image.open(ROOT/'gfx/interface/APDC/cold_war/pie_0.png').getchannel('A')
    for radius in [16,32,64,96]:
        x=128+math.sin(math.radians(.5))*radius;y=128-math.cos(math.radians(.5))*radius
        patch=alpha.crop((int(x)-2,int(y)-2,int(x)+3,int(y)+3))
        assert patch.getextrema()[1]>0,('hollow sector',radius)
    result={'button_extents':extents,'three_tabs_stack_like_cooperation':True,'one_shared_switch_cost':True,'solid_pie_interior':True,'boundary':'Native texture geometry and script bindings; does not send mouse or keyboard input.'}
    out=OUT/'ui-fixes';out.mkdir(exist_ok=True);(out/'ui-audit.json').write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps(result))

if __name__=='__main__':run()
