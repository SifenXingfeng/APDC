"""Install-format conversion of supplied icons and verified model packs into staging."""
from pathlib import Path
import hashlib,json,shutil,re,io
from PIL import Image,ImageOps,ImageDraw,ImageFont
from catalog import MODELS,MODEL_BY_INDEX,EQUIPMENT_NAMES
from cw import parse,patches
from build_core import ROOT,WORK,STAGE,emit

PACKS = ['通用车辆五套模型_待接入','第二批十套模型_待接入','模型收尾_涅托与武器变体','剩余六套单位与步枪_待接入']

def main():
    copied=[]
    for label in PACKS:
        pack=Path('D:/Desktop')/label
        records=json.loads((pack/'游戏资源校验清单.json').read_text('utf8'))
        for r in records:
            source=pack/'待接入游戏文件'/r['path']
            payload=source.read_bytes()
            assert hashlib.sha256(payload).hexdigest()==r['sha256'],('stale model source',str(source))
            rel=Path(r['path'])
            if 'APDC_b2_nyto' in rel.as_posix():continue # superseded by approved final Nyto
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True)
            if rel.name=='APDC_b2_models.asset':
                text=payload.decode('utf8'); edits=[]
                for n in parse(text):
                    if n.val('name')=='APDC_b2_nyto_entity':edits.append((n.start,n.end,''))
                payload=patches(text,edits).encode('utf8')
            elif rel.name=='APDC_b2_models.gfx':
                text=payload.decode('utf8');edits=[]
                for root in parse(text):
                    for n in root.children:
                        if n.val('name')=='APDC_b2_nyto_mesh':edits.append((n.start,n.end,''))
                payload=patches(text,edits).encode('utf8')
            elif rel.name=='APDC_r6_models.asset':
                # A later, approved infantry rebind supersedes the desktop pack's
                # simplified rig. Preserve only this entity, not unrelated R6 edits.
                current=ROOT/rel
                if current.is_file():
                    live=current.read_text('utf-8-sig')
                    live_node=next((n for n in parse(live) if n.val('name')=='APDC_r6_infantry_entity'),None)
                    if live_node and live_node.val('pdxmesh')=='APDC_vanilla_infantry_mesh':
                        text=payload.decode('utf8')
                        old=next(n for n in parse(text) if n.val('name')=='APDC_r6_infantry_entity')
                        payload=patches(text,[(old.start,old.end,live[live_node.start:live_node.end])]).encode('utf8')
            target.write_bytes(payload)
            copied.append({'path':rel.as_posix(),'source':str(source),'sha256':hashlib.sha256(payload).hexdigest()})
    units=json.loads((WORK/'normalized_units.json').read_text('utf8'))
    icon_dir=STAGE/'gfx/interface/apdc_units';icon_dir.mkdir(parents=True,exist_ok=True)
    sprites=[]; entity_text=[]; mappings=[]
    def sprite(name,rel,frames=1):
        sprites.append(f' spriteType = {{ name = "{name}" textureFile = "{rel}" noOfFrames = {frames} }}')
    for unit in units:
        uid=unit['id'];index=unit['index']
        im=Image.open(WORK/'design'/unit['icon']).convert('RGBA')
        assert im.size==(76,42)
        # Supplied frame is retained pixel-for-pixel. Second frame is also supplied art,
        # not an invented NATO icon; NATO conversion is not part of this integration.
        strip=Image.new('RGBA',(152,42));strip.paste(im,(0,0));strip.paste(im,(76,0))
        strip.save(icon_dir/(uid+'.dds'))
        small=ImageOps.contain(im,(30,12),Image.Resampling.LANCZOS)
        white=Image.new('RGBA',small.size,(255,255,255,0));white.putalpha(small.getchannel('A'))
        st=Image.new('RGBA',(60,12));st.paste(white,((30-white.width)//2,(12-white.height)//2));st.paste(white,(30+(30-white.width)//2,(12-white.height)//2))
        st.save(icon_dir/(uid+'_small.dds'))
        sprite('GFX_unit_'+uid+'_icon_medium','gfx/interface/apdc_units/'+uid+'.dds',2)
        sprite('GFX_unit_'+uid+'_icon_medium_white','gfx/interface/apdc_units/'+uid+'_small.dds',2)
        # A stable sprite name bypasses national equipment appearance selection.
        model=MODEL_BY_INDEX.get(index,'infantry')
        ename=uid+'_entity'
        if isinstance(model,tuple):
            primary,secondary=model
            entity_text.append(f'''entity = {{
 name = "{ename}"
 pdxmesh = "frame_artillery_mesh"
 default_state = "idle"
 scale = 1
 attach = {{ name = artillery artillery = "{MODELS[primary]}" }}
 attach = {{ name = infantry infantry = "{MODELS[secondary]}" }}
'''+''.join(f' state = {{ name = "{s}" animation = "idle" propagate_state = {{ artillery = "{s}" infantry = "{s if primary!="towed" or s not in ("attack","defend","support_attack") else "idle"}" }} }}\n' for s in ('idle','move','retreat','attack','defend','support_attack','training','death'))+'}\n')
        else:
            entity_text.append(f'entity = {{ clone = "{MODELS[model]}" name = "{ename}" }}\n')
        for suffix in ('_desert','_snow'):
            entity_text.append(f'entity = {{ clone = "{ename}" name = "{ename}{suffix}" }}\n')
        mappings.append({'unit':uid,'model':model,'entity':ename})
    # Preserve the previously requested Madagascar penguin exception.
    entity_text.append('entity = { clone = "MAD_infantry_entity" name = "MAD_apdc_infantry_entity" }\n')
    for suffix in ('_desert','_snow'):
        entity_text.append(f'entity = {{ clone = "MAD_infantry_entity{suffix}" name = "MAD_apdc_infantry_entity{suffix}" }}\n')
    sprite('GFX_group_combat_support_icon','gfx/interface/apdc_units/apdc_basic_robot.dds',2)
    # Production icons reuse the corresponding supplied unit artwork as a documented first version.
    for eq,name in EQUIPMENT_NAMES.items():
        archetype='apdc_'+eq+'_equipment'
        unit=next(u for u in units if archetype in u['data']['need'])
        im=Image.open(WORK/'design'/unit['icon']).convert('RGBA')
        icon=Image.new('RGBA',(156,104));scaled=im.resize((152,84),Image.Resampling.LANCZOS)
        icon.paste(scaled,(2,10));icon.save(icon_dir/('eq_'+eq+'.dds'))
        for k in ('GFX_apdc_eq_'+eq,'GFX_'+archetype+'_medium','GFX_'+archetype+'_1_medium','GFX_'+archetype+'_1_small'):
            sprite(k,'gfx/interface/apdc_units/eq_'+eq+'.dds')
    emit('interface/zz_APDC_unit_icons.gfx','spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n')
    emit('gfx/entities/zzz_APDC_unit_mapping.asset','# Approved model packs and unit appearances.\n'+''.join(entity_text))
    # Later animation/material revisions supersede the original desktop packs.
    # Preserve only registered, hash-verified files; unknown edits must be reviewed.
    refresh_manifest=ROOT/'art_source/unit_motion_refresh/backup/manifest.json'
    if refresh_manifest.exists():
        refresh=json.loads(refresh_manifest.read_text('utf8'))
        for rel,record in refresh.items():
            live=ROOT/rel
            if not live.exists():raise FileNotFoundError(live)
            data=live.read_bytes()
            assert hashlib.sha256(data).hexdigest()==record['installed_sha256'],('changed motion revision',rel)
            target=STAGE/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            copied=[r for r in copied if r['path']!=rel]
            copied.append({'path':rel,'source':str(live),'sha256':record['installed_sha256']})
        for mapping in mappings:
            if mapping['unit']=='apdc_ump_sisters':mapping['model']='ump_chibi'
    (WORK/'model_install_manifest.json').write_text(json.dumps(copied,ensure_ascii=False,indent=2),'utf8')
    (WORK/'unit_model_mapping.json').write_text(json.dumps(mappings,ensure_ascii=False,indent=2),'utf8')
    # Pixel-preservation and visual inventory, QA only.
    sheet=Image.new('RGB',(900,((len(units)+5)//6)*94),(34,39,46))
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',11)
    for i,u in enumerate(units):
        x=(i%6)*150;y=(i//6)*94
        im=Image.open(WORK/'design'/u['icon']).convert('RGBA')
        sheet.paste(im,(x+36,y+6),im)
        draw.text((x+3,y+55),f'{u["index"]:02d} '+u['name'][:12],font=font,fill='white')
    sheet.save(WORK/'兵牌接入校验.png')
    print(json.dumps({'model_files':len(copied),'icon_textures':len(list(icon_dir.glob('*.dds'))),'unit_mappings':len(mappings)},ensure_ascii=False))

if __name__=='__main__':main()
