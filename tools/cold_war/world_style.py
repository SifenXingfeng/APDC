"""Display overrides restricted to the Cold War world map; original masks stay intact."""
import io,json
from PIL import Image
from common import ROOT,metadata,parse,block,write

UNINHABITED='ZZZ'
PREFIX='gfx/interface/APDC/cold_war/world_style'

def black_sprite(index):return f'GFX_APDC_cw_world_black_{index}'

def save_png(image,path):
    stream=io.BytesIO();image.save(stream,format='PNG');data=stream.getvalue()
    if not path.exists() or path.read_bytes()!=data:path.write_bytes(data)

def apply_assets():
    g=metadata();dest=ROOT/PREFIX;dest.mkdir(parents=True,exist_ok=True);defs=[]
    for entry in g['pieces']:
        w=entry['world'];source=Image.open(ROOT/'gfx/interface/APDC/cold_war/map'/f'world_{entry["id"]}.png').convert('RGBA')
        alpha=source.crop((0,0,w['w'],w['h'])).getchannel('A')
        black=Image.new('RGBA',alpha.size,(0,0,0,0));black.putalpha(alpha)
        path=f'{PREFIX}/black_{entry["id"]}.png';save_png(black,ROOT/path)
        defs.append(block('spriteType',f'name = "{black_sprite(entry["id"])}" texturefile = "{path}" transparencecheck = yes'))
    targets={}
    for entry in g['borders']:
        source=Image.open(ROOT/'gfx/interface/APDC/cold_war/map'/f'world_b{entry["id"]}.png').convert('RGBA')
        red=Image.new('RGBA',source.size,(255,0,0,0));red.putalpha(source.getchannel('A'))
        sheet=Image.new('RGBA',(source.width*2,source.height));sheet.paste(source,(0,0));sheet.paste(red,(source.width,0))
        path=f'{PREFIX}/border_{entry["id"]}.png';save_png(sheet,ROOT/path);targets[entry['world']['image']]=path
    gfx=ROOT/'interface/APDC_cold_war.gfx';text=gfx.read_text('utf-8');edits=[]
    for node in parse(text)[0].children:
        if node.val('name') not in targets:continue
        texture=node.get('texturefile');edits.append((texture.value_start,texture.value_end,'"'+targets[node.val('name')]+'"'))
        frames=node.get('noOfFrames')
        if frames:edits.append((frames.value_start,frames.value_end,'2'))
        else:edits.append((node.value_end-1,node.value_end-1,'noOfFrames = 2\n'))
    assert len([1 for a,b,c in edits if c.startswith('"')])==len(targets)
    for start,end,replacement in sorted(edits,reverse=True):text=text[:start]+replacement+text[end:]
    if gfx.read_text('utf-8')!=text:gfx.write_text(text,'utf-8')
    write('interface/APDC_cold_war_world_styles.gfx',block('spriteTypes',''.join(defs)))
    print(json.dumps({'world_black_masks':len(g['pieces']),'two_frame_world_borders':len(g['borders']),'scope':'Cold War world only; source PNGs and detail textures unchanged'}))

if __name__=='__main__':apply_assets()
