"""Native button feedback, without changing the map's normal-state artwork."""
from PIL import Image
from common import ROOT,parse,metadata,block,write

OPTION_SHADER='gfx/FX/APDC_buttonstate_optional_art.shader'

def apply_assets():
    image=Image.open(ROOT/'gfx/interface/APDC/cold_war/option.png').convert('RGBA')
    assert image.size==(184,30)
    image.crop((0,0,92,30)).save(ROOT/'gfx/interface/APDC/cold_war/option_first.png')
    definitions=[
        block('spriteType','name = "GFX_APDC_cw_return" texturefile = "gfx/interface/APDC/cold_war/option_first.png" noOfFrames = 1 effectFile = "gfx/FX/buttonstate.shader"'),
        block('spriteType',f'name = "GFX_APDC_cw_law_option_feedback" texturefile = "gfx/interface/APDC/cold_war/option_first.png" noOfFrames = 1 effectFile = "{OPTION_SHADER}"'),
    ]
    gfx=ROOT/'interface/APDC_cold_war.gfx'
    cooperation=ROOT/'interface/APDC_cooperation_organizations.gfx'
    available=next(n for n in parse(cooperation.read_text('utf-8'))[0].children if n.val('name')=='GFX_APDC_cooperation_law_option_available')
    texture=next(n.value.strip('"') for n in available.children if n.key.lower()=='texturefile')
    definitions.append(block('spriteType',f'name = "GFX_APDC_cooperation_law_option_feedback" texturefile = "{texture}" noOfFrames = 1 effectFile = "{OPTION_SHADER}"'))
    write('interface/APDC_button_feedback.gfx',block('spriteTypes',''.join(definitions)))
    # Whole-country hover coupling is not implemented. Keep world inputs
    # static in Over/Down, while retaining their original disabled rendering.
    body=gfx.read_text('utf-8');targets={e['world']['image'] for e in metadata()['pieces']};edits=[]
    for node in parse(body)[0].children:
        if node.val('name') not in targets:continue
        effect=next((n for n in node.children if n.key.lower()=='effectfile'),None)
        value='"gfx/FX/buttonstate_onlydisable.shader"'
        if effect:edits.append((effect.value_start,effect.value_end,value))
        else:edits.append((node.value_end-1,node.value_end-1,'effectFile = '+value+'\n'))
    for start,end,value in sorted(edits,reverse=True):body=body[:start]+value+body[end:]
    if body!=gfx.read_text('utf-8'):gfx.write_text(body,'utf-8')
    # Keep native window backgrounds (and dragging), but make all input states
    # use the unmodified image. Never alter a global/default button shader.
    for path,name in [(gfx,'GFX_APDC_cw_background'),
                      (cooperation,'GFX_APDC_cooperation_organization_panel_main'),
                      (ROOT/'interface/APDC_cabinet.gfx','GFX_APDC_cabinet_member_panel_bg')]:
        body=path.read_text('utf-8')
        node=next(n for n in parse(body)[0].children if n.val('name')==name)
        effect=next((n for n in node.children if n.key.lower()=='effectfile'),None)
        if effect:
            body=body[:effect.value_start]+'"gfx/FX/static_button.shader"'+body[effect.value_end:]
        else:
            body=body[:node.value_end-1]+'effectFile = "gfx/FX/static_button.shader"\n'+body[node.value_end-1:]
        if body!=path.read_text('utf-8'):path.write_text(body,'utf-8')

if __name__=='__main__':apply_assets()
