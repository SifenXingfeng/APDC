"""Generate actual state masks/borders and bounded detail-map LODs; no map edits."""
import csv, json, math, re, colorsys, shutil, sys
sys.path.insert(0, "D:/APDC_ColdWarTools/pydeps")
from scipy.ndimage import distance_transform_edt
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from common import ROOT, GAME, ART, OUT, parse, write, block

SCALES=[2**(-4+i/2) for i in range(26)]
PREFIX='gfx/interface/APDC/cold_war'

def country_colors():
    registry={};colors={};cosmetics={}
    for base in (GAME,ROOT):
        for p in sorted((base/'common/country_tags').glob('*.txt')):
            for n in parse(p.read_text('utf-8-sig')):
                if n.value:registry[n.key]=n.value.strip('"')
    for tag,rel in registry.items():
        p=ROOT/'common'/rel
        if not p.exists():p=GAME/'common'/rel
        if p.exists():
            m=re.search(r'\bcolor\s*=\s*(?:(rgb|hsv)\s*)?\{\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)',p.read_text('utf-8-sig'))
            if m:
                v=[float(m[i]) for i in (2,3,4)]
                colors[tag]=[round(c*255) for c in colorsys.hsv_to_rgb(*v)] if m[1]=='hsv' else [round(c) for c in v]
    for base in (GAME,ROOT):
        p=base/'common/countries/colors.txt'
        if not p.exists():continue
        t=p.read_text('utf-8-sig')
        for n in parse(t):
            m=re.search(r'\bcolor\s*=\s*(?:(rgb|hsv)\s*)?\{\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)',t[n.start:n.end])
            if m:
                v=[float(m[i]) for i in (2,3,4)]
                val=[round(c*255) for c in colorsys.hsv_to_rgb(*v)] if m[1]=='hsv' else [round(c) for c in v]
                (colors if n.key in registry else cosmetics)[n.key]=val
    return registry,colors,cosmetics

def build():
    dest=ROOT/PREFIX;dest.mkdir(parents=True,exist_ok=True)
    # The edited panel background is now a project-owned source asset.
    # Do not restore the older desktop image containing the baked exit arrow.
    assert (dest/'background.png').exists()
    for name,src in [('tabs','控制标签.png'),('control','控制面板页.png'),('law','冷战法案.png'),('option','执行按钮.png')]:
        shutil.copy2(ART/src,dest/(name+'.png'))
    option=Image.open(ART/'执行按钮.png').convert('RGBA')
    # User-defined frame 1=available, frame 2=current; unavailable is grayscale.
    g=option.crop((0,0,92,30)).convert('LA').convert('RGBA');g.save(dest/'option_disabled.png')
    Image.new('RGBA',(1,1),(0,0,0,0)).save(dest/'empty.png')
    registry,colors,cosmetics=country_colors()
    allcolors={**colors,**cosmetics};palette_ids={tag:i+1 for i,tag in enumerate(sorted(allcolors))}
    pal=Image.new('RGBA',(len(palette_ids),1));pal.putdata([tuple(allcolors[tag])+(255,) for tag in sorted(allcolors)]);pal.save(dest/'palette.png')
    states={};prov={}
    for p in (ROOT/'history/states').glob('*.txt'):
        s=next(n for n in parse(p.read_text('utf-8-sig')) if n.key=='state');sid=int(s.val('id'))
        states[sid]={'owner':s.get('history').val('owner')}
        for n in s.get('provinces').children:prov[int(n.key)]=sid
    lut=np.zeros(1<<24,dtype=np.uint16)
    for row in csv.reader((ROOT/'map/definition.csv').read_text('utf-8-sig').splitlines(),delimiter=';'):
        try:pid,r,g,b=map(int,row[:4])
        except (ValueError,IndexError):continue
        if pid in prov:lut[r+(g<<8)+(b<<16)]=prov[pid]
    arr=np.asarray(Image.open(ROOT/'map/provinces.bmp'),dtype=np.uint32)
    raster=lut[arr[:,:,0]+(arr[:,:,1]<<8)+(arr[:,:,2]<<16)];H,W=raster.shape
    land=raster>0;thin=np.zeros((H,W),bool);coast=np.zeros((H,W),bool)
    boundaries=defaultdict(list)
    for axis in (0,1):
        a=raster[:-1,:] if axis==0 else raster[:,:-1];b=raster[1:,:] if axis==0 else raster[:,1:]
        yy,xx=np.nonzero(a!=b)
        for y,x in zip(yy,xx):
            v1=int(a[y,x]);v2=int(b[y,x]);p1=(int(x),int(y));p2=(int(x+(axis==1)),int(y+(axis==0)))
            thin[p1[1],p1[0]]=True;thin[p2[1],p2[0]]=True
            if v1 and v2:boundaries[tuple(sorted((v1,v2)))].extend((p1,p2))
            else:coast[p1[1],p1[0]]=True;coast[p2[1],p2[0]]=True
    yy=np.flatnonzero((raster[:,0]!=raster[:,-1])&(raster[:,0]>0)&(raster[:,-1]>0))
    for y in yy:boundaries[tuple(sorted((int(raster[y,0]),int(raster[y,-1]))))].extend(((0,int(y)),(W-1,int(y))))
    # Native pixel bounds for each fixed state; current ownership remains runtime data.
    xmin=np.full(max(states)+1,W);xmax=np.zeros(max(states)+1,dtype=int);ymin=np.full(max(states)+1,H);ymax=np.zeros(max(states)+1,dtype=int)
    flat=raster.ravel();xx=np.tile(np.arange(W),H);yy=np.repeat(np.arange(H),W)
    np.minimum.at(xmin,flat,xx);np.maximum.at(xmax,flat,xx);np.minimum.at(ymin,flat,yy);np.maximum.at(ymax,flat,yy)
    sxmin=np.full(max(states)+1,W);sxmax=np.zeros(max(states)+1,dtype=int)
    shifted_x=(xx+W//2)%W;np.minimum.at(sxmin,flat,shifted_x);np.maximum.at(sxmax,flat,shifted_x)
    zoom_limits={sid:min(460/min(int(xmax[sid]-xmin[sid]+1),int(sxmax[sid]-sxmin[sid]+1)),430/int(ymax[sid]-ymin[sid]+1)) for sid in states}
    pieces=[];gfx=[]
    progress_steps=len(palette_ids)*len(SCALES)+1
    def sprite(name,path,frames=1):
        gfx.append(block('spriteType',f'name = "{name}"\ntexturefile = "{PREFIX}/{path}"\ntransparencecheck = yes\n'+(f'noOfFrames = {frames}' if frames>1 else '')))
    def progress(name,path,w,h,kind=0):
        gfx.append(block('progressbartype',f'name = "{name}"\ntextureFile1 = "{PREFIX}/{path}"\ntextureFile2 = "{PREFIX}/palette.png"\ncolor = {{ {kind} 0 0 0 }}\nsize = {{ x = {w} y = {h} }}\nsteps = {progress_steps}\neffectFile = "gfx/FX/apdc_cw_palette.shader"'))
    def asset(mask,x0,y0,name,kind='state',max_scale=999):
        # A single signed-distance texture is shared by all zoom containers.
        # Distances are stored in source pixels, so the shader keeps strokes
        # the same on-screen thickness at every zoom level.
        hh,ww=mask.shape[:2];pad=64
        rgba=np.zeros((hh+2*pad,ww+2*pad,4),np.uint8)
        fill=np.pad(mask[:,:,0]>0,pad)
        if kind=='state':
            signed=distance_transform_edt(fill)-distance_transform_edt(~fill)
            rgba[:,:,0]=np.clip(np.rint(127.5+signed*2),0,255).astype('uint8')
            for channel in [1,2]:
                boundary=np.pad(mask[:,:,channel]>0,pad)
                distance=distance_transform_edt(~boundary) if boundary.any() else np.full(fill.shape,128.)
                rgba[:,:,channel]=np.clip(np.rint(distance*2),0,255).astype('uint8')
        else:
            distance=distance_transform_edt(~np.pad(mask[:,:,3]>0,pad))
            rgba[:,:,0]=np.clip(np.rint(distance*2),0,255).astype('uint8')
        rgba[:,:,3]=255
        path=f'map/{name}.png';(dest/'map').mkdir(exist_ok=True)
        Image.fromarray(rgba).save(dest/path)
        spr='GFX_APDC_cw_'+name;progress(spr,path,rgba.shape[1],rgba.shape[0],int(kind!='state'))
        return {'name':name,'x':x0,'y':y0,'w':ww,'h':hh,'padding':pad,'image':spr}
    # Longitude strips keep wrapped/overseas states from becoming giant empty quads.
    strip=W//8
    for sid,state in sorted(states.items()):
        shifted=[]
        for chunk in range(8):
            left=max(int(xmin[sid]),chunk*strip);right=min(int(xmax[sid])+1,(chunk+1)*strip)
            if right<=left:continue
            top=int(ymin[sid]);bottom=int(ymax[sid])+1
            view=raster[top:bottom,left:right]==sid
            ry,rx=np.nonzero(view)
            if not len(rx):continue
            x0=left+int(rx.min());y0=top+int(ry.min());x1=left+int(rx.max())+1;y1=top+int(ry.max())+1
            fill=(raster[y0:y1,x0:x1]==sid)
            rgba=np.zeros((*fill.shape,4),np.uint8);rgba[:,:,0]=fill*255;rgba[:,:,1]=(thin[y0:y1,x0:x1]&fill)*200;rgba[:,:,2]=(coast[y0:y1,x0:x1]&fill)*255;rgba[:,:,3]=fill*255
            n=len(pieces);e=asset(rgba,x0,y0,f's{sid}_{chunk}',max_scale=zoom_limits[sid]);e.update({'id':n,'state':sid,'kind':'state'})
            # Full-map quad and alpha are generated directly from current raster data.
            scale=1000/W;wx=math.floor(x0*scale);wy=math.floor(y0*scale)
            fw=max(1,math.ceil(x1*scale)-wx);fh=max(1,math.ceil(y1*scale)-wy)
            alpha=Image.fromarray((fill*255).astype('uint8')).resize((fw,fh),Image.Resampling.LANCZOS)
            sheet=Image.new('RGBA',(fw*4,fh))
            for j,col in enumerate([(201,45,57),(102,108,116),(44,131,210),(235,123,161)]):
                tile=Image.new('RGBA',(fw,fh),col+(255,));tile.putalpha(alpha);sheet.paste(tile,(j*fw,0))
            file=f'map/world_{n}.png';sheet.save(dest/file);sprite(f'GFX_APDC_cw_world_{n}',file,4)
            e['world']={'x':wx,'y':wy,'w':fw,'h':fh,'image':f'GFX_APDC_cw_world_{n}'};pieces.append(e)
            shifted.extend((((x0+W//2)%W),((x1-1+W//2)%W)))
        state.update({'x0':int(xmin[sid]),'x1':int(xmax[sid])+1,'y0':int(ymin[sid]),'y1':int(ymax[sid])+1,'shift_x0':min(shifted),'shift_x1':max(shifted)+1})
    borders=[]
    for pair,points in sorted(boundaries.items()):
        points=np.unique(np.asarray(points),axis=0)
        for chunk in range(8):
            part=points[(points[:,0]>=chunk*strip)&(points[:,0]<(chunk+1)*strip)]
            if not len(part):continue
            x0,y0=part.min(0);x1,y1=part.max(0)+1;mask=np.zeros((int(y1-y0),int(x1-x0),4),np.uint8)
            mask[part[:,1]-y0,part[:,0]-x0,:]=255
            n=len(borders);e=asset(mask,int(x0),int(y0),f'b{n}','border',max(zoom_limits[pair[0]],zoom_limits[pair[1]]));e.update({'id':n,'a':pair[0],'b':pair[1],'kind':'border'})
            scale=1000/W;wx=math.floor(x0*scale);wy=math.floor(y0*scale);fw=max(1,math.ceil(x1*scale)-wx);fh=max(1,math.ceil(y1*scale)-wy)
            alpha=Image.fromarray(mask[:,:,3]).resize((fw,fh),Image.Resampling.LANCZOS)
            tile=Image.new('RGBA',(fw,fh),(174,206,225,0));tile.putalpha(alpha);file=f'map/world_b{n}.png';tile.save(dest/file);sprite(f'GFX_APDC_cw_world_b{n}',file)
            e['world']={'x':wx,'y':wy,'w':fw,'h':fh,'image':f'GFX_APDC_cw_world_b{n}'};borders.append(e)
    coastalpha=Image.fromarray((coast*255).astype('uint8')).resize((1000,500),Image.Resampling.LANCZOS)
    ci=Image.new('RGBA',(1000,500),(118,163,181,0));ci.putalpha(coastalpha);ci.save(dest/'coasts.png');sprite('GFX_APDC_cw_coasts','coasts.png')
    for name,path,frames in [('background','background.png',1),('tabs','tabs.png',1),('control','control.png',1),('law','law.png',1),('option','option.png',2),('option_disabled','option_disabled.png',1),('empty','empty.png',1)]:sprite('GFX_APDC_cw_'+name,path,frames)
    # Reuse cabinet geometry, but with project country colours instead of ideologies.
    alpha=Image.new('L',(2048,2048));draw=ImageDraw.Draw(alpha)
    draw.pieslice((0,0,2047,2047),start=-90,end=-89,fill=255)
    alpha=alpha.resize((256,256),Image.Resampling.LANCZOS)
    # Split country palette into small atlases so texture dimensions remain bounded.
    for group in range(math.ceil(len(palette_ids)/32)):
        count=min(32,len(palette_ids)-group*32);im=Image.new('RGBA',(count*256,256))
        for j,tag in enumerate(sorted(allcolors)[group*32:(group+1)*32]):
            tile=Image.new('RGBA',(256,256),tuple(allcolors[tag])+(255,));tile.putalpha(alpha);im.paste(tile,(j*256,0))
        path=f'pie_{group}.png';im.save(dest/path);sprite(f'GFX_APDC_cw_pie_{group}',path,count)
    # Legend swatches use the same palette, with native alpha detection.
    sw=Image.new('RGBA',(16*len(palette_ids),16))
    for j,tag in enumerate(sorted(allcolors)):sw.paste(tuple(allcolors[tag])+(255,),(j*16,0,(j+1)*16,16))
    sw.save(dest/'swatches.png');sprite('GFX_APDC_cw_swatches','swatches.png',len(palette_ids))
    write('interface/APDC_cold_war.gfx',block('spriteTypes',''.join(gfx)))
    shader=(ROOT/'gfx/FX/apdc_cw_palette.shader')
    template=(Path('D:/SteamLibrary/steamapps/workshop/content/394360/2438003901/gfx/FX/map_fill_palette.shader').read_text('utf-8-sig'))
    template=template.replace('MagFilter = "Point"','MagFilter = "Linear"',1).replace('MinFilter = "Point"','MinFilter = "Linear"',1)
    start=template.index('\t\t\t// Map Fill Palette Shader');end=template.index('\n\t\t}',start)
    body=f'''            float4 mask = tex2D(TextureOne, v.vTexCoord0.xy);
            float packed = floor(CurrentState * {progress_steps}.f + 0.5f)-1.f;
            float z = floor(packed / {len(palette_ids)}.f);
            float paletteSlot = packed - z*{len(palette_ids)}.f;
            float zoom = exp2(-4.f + z*0.5f);
            float4 fill = tex2D(TextureTwo, float2((paletteSlot+0.5f)/{len(palette_ids)}.f,0.5f));
            float distance = (mask.r*255.f-127.5f)*0.5f;
            float alpha = smoothstep(-0.5f,0.5f,distance*zoom);
            float edge = mask.b*127.5f*zoom;
            float fine = 1.f-smoothstep(0.5f,1.1f,mask.g*127.5f*zoom);
            float3 col = lerp(fill.rgb,float3(0.54f,0.72f,0.86f),fine*0.8f);
            if (vFirstColor.r>0.5f) {{ edge=mask.r*127.5f*zoom; alpha=0.f; col=float3(0.55f,0.75f,0.94f); }}
            float halo=1.f-smoothstep(1.f,2.f,edge);
            float core=1.f-smoothstep(0.4f,1.1f,edge);
            col=lerp(col,float3(0.55f,0.75f,0.94f),halo);
            col=lerp(col,float3(0.89f,0.96f,1.f),core);
            alpha=max(alpha,halo);
            return float4(col,alpha);'''
    write('gfx/FX/apdc_cw_palette.shader',template[:start]+body+template[end:])
    result={'width':W,'height':H,'states':states,'pieces':pieces,'borders':borders,'scales':SCALES,'palette_ids':palette_ids,'colors':allcolors,'registry':registry}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'geometry.json').write_text(json.dumps(result,separators=(',',':')),'utf-8')
    print(json.dumps({'states':len(states),'pieces':len(pieces),'border_pieces':len(borders),'palette':len(palette_ids),'assets':len(gfx)}))

if __name__=='__main__':build()
