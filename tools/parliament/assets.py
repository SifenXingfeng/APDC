"""Copy supplied artwork and generate deterministic seats and progress masks."""
from io import BytesIO
from zipfile import ZipFile
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageOps
from common import *


def png(rel, im):
    out=BytesIO();im.save(out,format='PNG');write(rel,out.getvalue())


def generate():
    gfx='';meta={}
    supplied={'background':'议会背景图.png','candidate_background':'内阁成员更换背景.png','latches':'议案进度卡扣.png','law_tile':'政治改革背景.png','special_row':'特殊议案背景.png','party_button':'党派法案小按钮.png','special_button':'特殊议案按钮.png'}
    for key,name in supplied.items():
        path=SOURCE/'ui'/name;dest='gfx/interface/APDC/parliament/'+key+'.png'
        write(dest,path.read_bytes())
        with Image.open(path) as im:meta[name]={'size':list(im.size),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        gfx+=block('spriteType','name = "GFX_apdc_parl_'+key+'"\ntexturefile = "'+dest+'"\n'+('noOfFrames = 2\n' if key=='latches' else '')+('transparencecheck = no\n' if key in ('background','candidate_background','party_button','special_button','law_tile') else '')+('effectFile = "gfx/FX/buttonstate.shader"\n' if key in ('party_button','special_button','law_tile') else ''))
    podium=SOURCE/'ui/议会入口.png';write('gfx/interface/APDC/parliament/entry.png',podium.read_bytes())
    gfx+=block('spriteType','name = "GFX_apdc_parl_entry"\ntexturefile = "gfx/interface/APDC/parliament/entry.png"\neffectFile = "gfx/FX/buttonstate.shader"')
    for name,number in [('candidate_card',2),('law_option_card',3)]:
        gfx+=block('spriteType','name = "GFX_apdc_parl_'+name+'"\ntexturefile = "gfx/interface/idea_entry_bg_'+str(number)+'.dds"\nnoOfFrames = 2\ntransparencecheck = no')
    for key,size in [('hit_47_63',(47,63)),('hit_74_98',(74,98)),('hit_150_24',(150,24)),('hit_249_73',(249,73))]:
        png('gfx/interface/APDC/parliament/'+key+'.png',Image.new('RGBA',size,(0,0,0,0)))
        gfx+=block('spriteType','name = "GFX_apdc_parl_'+key+'"\ntexturefile = "gfx/interface/APDC/parliament/'+key+'.png"\ntransparencecheck = no')
    empty=Image.new('RGBA',(156,210),(0,0,0,0));draw=ImageDraw.Draw(empty)
    draw.rectangle((1,1,154,208),fill=(31,34,42,210),outline=(140,140,144,240),width=3)
    with Image.open(GAME/'gfx/interface/officer_corp/select_advisor.dds') as plus:
        plus=plus.convert('RGBA');plus.thumbnail((78,78),Image.Resampling.LANCZOS)
        empty.alpha_composite(plus,((156-plus.width)//2,(210-plus.height)//2))
    png('gfx/interface/APDC/parliament/empty_slot.png',empty)
    gfx+=block('spriteType','name = "GFX_apdc_parl_empty_slot"\ntexturefile = "gfx/interface/APDC/parliament/empty_slot.png"')
    # The Word file contains the nine actual supplied 64px regime icons.
    regimes=load_json('regimes.json');by_name={v['name']:k for k,v in regimes.items()}
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
    found=set()
    with ZipFile(SOURCE/'documents/regimes.docx') as z:
        rels={n.attrib['Id']:n.attrib['Target'] for n in ET.fromstring(z.read('word/_rels/document.xml.rels'))}
        current=None
        for el in ET.fromstring(z.read('word/document.xml')).find('w:body',ns):
            text=''.join(n.text or '' for n in el.findall('.//w:t',ns)).strip()
            if text in by_name:current=by_name[text]
            for blip in el.findall('.//a:blip',ns):
                if current:
                    raw=z.read('word/'+rels[blip.attrib['{'+ns['r']+'}embed']]);dest='gfx/interface/APDC/parliament/regimes/'+current+'.png'
                    write(dest,raw);found.add(current)
                    gfx+=block('spriteType','name = "GFX_apdc_parl_regime_'+current+'"\ntexturefile = "'+dest+'"')
    assert found==set(regimes)
    # Read the current palette, including the old conservative/liberal order.
    old_order=['communism','socialism','social_democracy','conservatism','liberalism','authoritarianism','dictatorship','fascism','fundamentalism']
    palette=[]
    swatch=ROOT/'gfx/interface/cabinet/APDC_cabinet_ideology_swatches.png'
    with Image.open(swatch) as im:
        w=im.width//9
        for p in PARTIES:palette.append(im.convert('RGBA').getpixel((old_order.index(p)*w+w//2,im.height//2)))
    for size,label in [(7,'large'),(3,'small')]:
        sheet=Image.new('RGBA',(size*9,size),(0,0,0,0));draw=ImageDraw.Draw(sheet)
        for i,color in enumerate(palette):draw.ellipse((i*size,0,(i+1)*size-1,size-1),fill=color)
        dest='gfx/interface/APDC/parliament/dots_'+label+'.png';png(dest,sheet)
        gfx+=block('spriteType','name = "GFX_apdc_parl_dot_'+label+'"\ntexturefile = "'+dest+'"\nnoOfFrames = 9')
    radii=[65+125*i/12 for i in range(13)]
    exact=[500*r/sum(radii) for r in radii];counts=[math.floor(v) for v in exact]
    for i in sorted(range(13),key=lambda i:(-(exact[i]-counts[i]),i))[:500-sum(counts)]:counts[i]+=1
    points=[]
    for row,(radius,count) in enumerate(zip(radii,counts)):
        for n in range(count):
            angle=math.pi*(n+0.5)/count
            points.append({'row':row,'angle':angle,'radius':radius,'x':radius*math.cos(angle),'y':-radius*math.sin(angle)})
    points.sort(key=lambda p:(-p['angle'],p['row']))
    assert len(points)==500 and sum(counts)==500
    json_write('tools/parliament/data/seat_layout.json',{'schema_version':1,'rows':13,'seats':500,'row_counts':counts,'order':'left_to_right_angle_then_inner_to_outer','points':points})
    # Ten short horizontal atlases stay below 16K GPU width. Every frame is
    # an exact crop of the provided fill; no reconstructed gradient is used.
    with Image.open(SOURCE/'ui/议案进度条.png') as bar:
        bar=bar.convert('RGBA')
        for i in range(10):
            x=i*101;w=min(101,bar.width-x);tile=bar.crop((x,0,x+w,bar.height))
            sheet=Image.new('RGBA',(w*(w+1),bar.height),(0,0,0,0))
            for n in range(w+1):sheet.paste(tile.crop((0,0,n,bar.height)),(n*w,0))
            dest='gfx/interface/APDC/parliament/progress_'+str(i)+'.png';png(dest,sheet)
            gfx+=block('spriteType','name = "GFX_apdc_parl_progress_'+str(i)+'"\ntexturefile = "'+dest+'"\nnoOfFrames = '+str(w+1))
    # Candidate portraits are author-owned native sprites. Preserve the fitted
    # legacy aliases; new portraits use ordinary independent .gfx definitions.
    previous=ROOT/'interface/apdc_parliament.gfx'
    if previous.exists():
        existing=previous.read_text('utf-8-sig')
        for node in walk(parse(existing)):
            if node.key.lower()=='spritetype' and (node.val('texturefile') or '').startswith('gfx/interface/APDC/parliament/portraits/'):
                gfx+=existing[node.start:node.end]+'\n'
    write('interface/apdc_parliament.gfx',block('spriteTypes',gfx))
    json_write('docs/parliament/20261107-implementation/artwork-audit.json',meta)
