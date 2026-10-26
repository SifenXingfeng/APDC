"""Political-page Cold War entry; preserve the supplied PNGs without resampling."""
from common import ROOT,parse,block,write
from PIL import Image
import struct

def write_background(path, image):
    """Keep native background paths valid, with lossless BGRA and alpha."""
    width,height=image.size
    header=b'DDS '+struct.pack('<31I',124,0x100f,height,width,width*4,0,0,
        *([0]*11),32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,
        0xff000000,0x1000,0,0,0,0)
    path.write_bytes(header+image.tobytes('raw','BGRA'))

def apply():
    background=Image.open(ROOT/'gfx/interface/APDC/politics/politics_background.png').convert('RGBA')
    assert background.size==(550,636)
    # The native political screen can select either original sprite at runtime.
    # Replace their textures as well as retaining the project-local PNG source.
    for filename in ('pol_view_bg.dds','pol_view_bg_no_dlc.dds'):
        write_background(ROOT/'gfx/interface'/filename,background)
    icon=Image.open(ROOT/'gfx/interface/APDC/politics/cold_war_entry.png').convert('RGBA')
    assert icon.size==(83,80)
    canvas=Image.new('RGBA',(93,92));canvas.paste(icon,(5,6))
    canvas.save(ROOT/'gfx/interface/APDC/politics/cold_war_entry_button.png')
    # The former top-bar sprite must not return when the map GFX is rebuilt.
    path=ROOT/'interface/APDC_cold_war.gfx';text=path.read_text('utf-8')
    obsolete=[node for node in parse(text)[0].children if node.val('name')=='GFX_APDC_cw_entry']
    for node in sorted(obsolete,key=lambda node:node.start,reverse=True):text=text[:node.start]+text[node.end:]
    if obsolete:path.write_text(text,'utf-8')
    write('interface/APDC_cold_war_politics_entry.gfx',block('spriteTypes','''spriteType = {
name = "GFX_APDC_cw_politics_entry"
texturefile = "gfx/interface/APDC/politics/cold_war_entry_button.png"
noOfFrames = 1
transparencecheck = no
effectFile = "gfx/FX/buttonstate.shader"
}
'''))

if __name__=='__main__':apply()
