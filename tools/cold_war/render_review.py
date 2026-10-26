"""Deterministic asset/layout review, explicitly not an in-engine screenshot."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from common import ROOT,OUT,metadata

ART=ROOT/'gfx/interface/APDC/cold_war'

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def map_detail(g,target):
    initial=json.loads((ROOT/'tools/map_maintenance/baseline/initial_territories.json').read_text('utf-8'))
    owned={int(sid):s for sid,s in g['states'].items() if s['owner']==target and target in initial[sid]['cores']}
    if not owned:return Image.new('RGBA',(500,500)),{'country':target,'core_states':0}
    y0=min(s['y0'] for s in owned.values());y1=max(s['y1'] for s in owned.values())
    orig=[]
    for mode in (0,1):
        lo=min(s['shift_x0' if mode else 'x0'] for s in owned.values());hi=max(s['shift_x1' if mode else 'x1'] for s in owned.values());orig.append((hi-lo,mode,lo))
    span,mode,x0=min(orig);z=max(i for i,s in enumerate(g['scales']) if span*s<=460 and (y1-y0)*s<=430);scale=g['scales'][z]
    ox=20+(460-span*scale)/2;oy=45+(430-(y1-y0)*scale)/2
    canvas=Image.new('RGBA',(500,500));color=np.array(g['colors'][target])/255
    entries=[(e,False) for e in g['pieces'] if e['state'] in owned]+[(e,True) for e in g['borders'] if (e['a'] in owned)!=(e['b'] in owned)]
    for e,border in entries:
        src=Image.open(ART/'map'/f'{e["name"]}.png').convert('RGBA')
        px=((e['x']+2560)%5120 if mode else e['x'])-x0-64;py=e['y']-y0-64
        left=ox+px*scale;top=oy+py*scale
        field=np.asarray(src.transform((500,500),Image.Transform.AFFINE,(1/scale,0,-left/scale,0,1/scale,-top/scale),Image.Resampling.BILINEAR,fillcolor=(255,255,255,255) if border else (0,255,255,255)),dtype=float)/255
        edge=(field[:,:,0] if border else field[:,:,2])*127.5*scale
        halo=1-smooth(1,2,edge);core=1-smooth(.4,1.1,edge)
        if border:col=np.zeros((500,500,3))+np.array([.55,.75,.94]);alpha=np.zeros((500,500))
        else:
            alpha=smooth(-.5,.5,(field[:,:,0]*255-127.5)*.5*scale)
            fine=1-smooth(.25,.75,field[:,:,1]*127.5*scale)
            col=np.array(color)[None,None,:]*(1-fine[:,:,None]*.8)+np.array([.54,.72,.86])[None,None,:]*fine[:,:,None]*.8
        col=col*(1-halo[:,:,None])+np.array([.55,.75,.94])*halo[:,:,None]
        col=col*(1-core[:,:,None])+np.array([.89,.96,1])*core[:,:,None]
        alpha=np.maximum(alpha,halo)
        yy,xx=np.mgrid[:500,:500];alpha*=((xx>=left)&(xx<left+src.width*scale)&(yy>=top)&(yy<top+src.height*scale))
        rgba=np.concatenate([np.clip(col*255,0,255),np.clip(alpha[:,:,None]*255,0,255)],axis=2).astype('uint8')
        canvas.alpha_composite(Image.fromarray(rgba))
    return canvas,{'country':target,'core_states':len(owned),'zoom':z,'scale':scale,'display_dimensions':[span*scale,(y1-y0)*scale],'pieces':sum(not b for _,b in entries),'borders':sum(b for _,b in entries)}

def run():
    g=metadata();out=OUT/'layout-review';out.mkdir(exist_ok=True)
    world=Image.open(ART/'background.png').convert('RGBA')
    for e in g['pieces']:
        tag=g['states'][str(e['state'])]['owner'];frame=0 if tag=='GER' else 2 if tag in ('FRA','LLU') else 1
        im=Image.open(ART/'map'/f'world_{e["id"]}.png');w=e['world'];tile=im.crop((frame*w['w'],0,(frame+1)*w['w'],w['h']))
        world.alpha_composite(tile,(38+w['x'],85+w['y']))
    for e in g['borders']:
        if g['states'][str(e['a'])]['owner']==g['states'][str(e['b'])]['owner']:continue
        w=e['world'];world.alpha_composite(Image.open(ART/'map'/f'world_b{e["id"]}.png'),(38+w['x'],85+w['y']))
    world.alpha_composite(Image.open(ART/'coasts.png'),(38,85));world.alpha_composite(Image.open(ART/'screen_overlay.png'),(38,85))
    world.save(out/'world-geography.png')
    results=[]
    for tag in ['GER','FRA','LLU','SOV','MLT']:
        detail,report=map_detail(g,tag);detail.save(out/(tag+'-detail.png'));results.append(report)
    (out/'results.json').write_text(json.dumps({'kind':'offline asset review; not in-engine screenshot','details':results},indent=2),'utf-8')
    print(json.dumps(results))

if __name__=='__main__':run()
