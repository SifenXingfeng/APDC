"""Small UI overlays; no map data or supplied originals are modified."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from common import ROOT, ART, write, metadata

def build():
    dest=ROOT/'gfx/interface/APDC/cold_war'
    bg=np.asarray(Image.open(dest/'background.png').convert('RGBA'))[85:585,38:1038,:3].astype(float)
    lum=bg@np.array([.2126,.7152,.0722]);lo,hi=np.percentile(lum,[1,99])
    alpha=np.rint((1-(.8+.2*np.clip((lum-lo)/max(hi-lo,1),0,1)))*255).astype('uint8')
    overlay=np.zeros((500,1000,4),np.uint8);overlay[:,:,3]=alpha
    Image.fromarray(overlay).save(dest/'screen_overlay.png')
    # As in the economic/cooperation panels, native input uses texture dimensions.
    # A 1x1 transparent sprite stays a 1x1 input region despite button.size.
    hit_sprites=''
    for w,h in [(91,45),(171,59),(215,28),(92,30)]:
        filename=f'hit_{w}_{h}.tga'
        Image.new('RGBA',(w,h)).save(dest/filename)
        hit_sprites+=f'spriteType = {{ name = "GFX_APDC_cw_hit_{w}_{h}" texturefile = "gfx/interface/APDC/cold_war/{filename}" noOfFrames = 1 }}\n'
    # Full one-degree sectors compose a solid pie. Keep its interior opaque.
    g=metadata();alpha=Image.new('L',(2048,2048));draw=ImageDraw.Draw(alpha)
    draw.pieslice((0,0,2047,2047),start=-90,end=-89,fill=255)
    alpha=alpha.resize((256,256),Image.Resampling.LANCZOS)
    tags=sorted(g['palette_ids'],key=g['palette_ids'].get)
    for group in range((len(tags)+31)//32):
        subset=tags[group*32:(group+1)*32];atlas=Image.new('RGBA',(256*len(subset),256))
        for j,tag in enumerate(subset):
            tile=Image.new('RGBA',(256,256),tuple(g['colors'][tag])+(255,));tile.putalpha(alpha);atlas.paste(tile,(j*256,0))
        atlas.save(dest/f'pie_{group}.png')
    write('interface/APDC_cold_war_hit.gfx','''spriteTypes = {
spriteType = { name = "GFX_APDC_cw_screen_overlay" texturefile = "gfx/interface/APDC/cold_war/screen_overlay.png" transparencecheck = yes }
'''+hit_sprites+'}')

if __name__=='__main__':build()
