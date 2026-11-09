"""Regenerate map geometry in isolation; install only geographic outputs.

Retains the native renderer, original shader, palette, pie, input feedback,
background, political entry and all non-map GUI children.
"""
from pathlib import Path
import sys,json,shutil,hashlib,copy,zipfile
import common
from common import ROOT,parse,block

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(n):return (n.key,n.value,n.op,tuple(canonical(c) for c in n.children))

def run(backup):
    real=ROOT;stage=backup.resolve()/'cold-war-stage';stage.mkdir(exist_ok=True)
    for rel in ['history/states','common/country_tags','common/countries','common/ideas']:
        shutil.copytree(real/rel,stage/rel,dirs_exist_ok=True)
    files=['map/definition.csv','map/provinces.bmp','gfx/interface/APDC/cold_war/background.png','tools/cold_war/laws.json','tools/cold_war/render_mode.json']
    for rel in files:
        p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(real/rel,p)
    out=stage/'docs/cold-war/20261024';out.mkdir(parents=True,exist_ok=True)
    common.ROOT=stage;common.OUT=out
    import build_map
    build_map.ROOT=stage;build_map.OUT=out
    # Use the already installed source art, independent of old desktop paths.
    source_art=stage/'source-art';source_art.mkdir(exist_ok=True)
    for filename,target in [('tabs.png','控制标签.png'),('control.png','控制面板页.png'),('law.png','冷战法案.png'),('option.png','执行按钮.png')]:
        shutil.copy2(real/'gfx/interface/APDC/cold_war'/filename,source_art/target)
    build_map.ART=source_art
    with zipfile.ZipFile(backup.resolve()/'project-before.zip') as archive:
        old=json.loads(archive.read('docs/cold-war/20261024/geometry.json'))
    # Geography-only refresh preserves the installed palette and its packed
    # shader protocol. Adding a newly registered country's palette slot requires
    # a separate coordinated palette/pie/shader migration, not an implicit sort.
    original_country_colors=build_map.country_colors
    excluded_palette_tags=[]
    def existing_palette_colors():
        registry,colors,cosmetics=original_country_colors()
        current={**colors,**cosmetics}
        assert all(current[tag]==color for tag,color in old['colors'].items() if tag in current), 'Country colors changed; handle palette migration explicitly'
        excluded_palette_tags.extend(sorted(set(current)-set(old['palette_ids'])))
        # Retired identities keep their installed protocol slots. Geography
        # cannot drop those slots or sort the appended South Asia entries.
        return registry,dict(old['colors']),{}
    build_map.country_colors=existing_palette_colors
    if '--reuse-map' not in sys.argv:build_map.build()
    else:existing_palette_colors()
    new=json.loads((out/'geometry.json').read_text('utf-8'))
    # build_map's temporary artwork uses sorted slots, but none of that
    # palette/pie artwork is installed by this geography-only workflow.
    # All installed view encodings must use the existing stable slot map.
    new['palette_ids']=old['palette_ids']
    assert old['scales']==new['scales'] and old['palette_ids']==new['palette_ids'] and old['colors']==new['colors']
    assert set(old['states']) <= set(new['states']), 'Removing/reusing a state needs an explicit migration'
    # Keep piece indices stable when new states/longitude pieces are appended.
    # Array IDs are persisted, while detail texture names identify state+strip.
    old_piece_ids={(e['state'],e['x']//(new['width']//8)):e['id'] for e in old['pieces']}
    used_piece_ids=set();piece_moves=[];new_pieces=[]
    for entry in new['pieces']:
        oldid=old_piece_ids.get((entry['state'],entry['x']//(new['width']//8)))
        if oldid is not None and oldid<len(new['pieces']):
            assert oldid not in used_piece_ids
            used_piece_ids.add(oldid);piece_moves.append((entry,oldid))
        else:new_pieces.append(entry)
    free_piece_ids=iter(sorted(set(range(len(new['pieces'])))-used_piece_ids))
    piece_moves.extend((entry,next(free_piece_ids)) for entry in new_pieces)
    piece_copies=[]
    for entry,stableid in piece_moves:
        previous=entry['id']
        piece_copies.append((f'world_{stableid}.png',(stage/'gfx/interface/APDC/cold_war/map'/f'world_{previous}.png').read_bytes()))
        entry['id']=stableid;entry['world']['image']=f'GFX_APDC_cw_world_{stableid}'
    for filename,data in piece_copies:(stage/'gfx/interface/APDC/cold_war/map'/filename).write_bytes(data)
    new['pieces'].sort(key=lambda e:e['id'])
    # Preserve existing border IDs wherever possible. Fill deleted slots using
    # the last surviving borders, instead of renumbering thousands of assets.
    def borderkey(e):return (e['a'],e['b'],e['x']//(new['width']//8))
    oldids={borderkey(e):e['id'] for e in old['borders']};used=set();unassigned=[];moves=[]
    for entry in new['borders']:
        oldid=oldids.get(borderkey(entry))
        if oldid is not None and oldid<len(new['borders']):used.add(oldid);moves.append((entry,oldid))
        else:unassigned.append(entry)
    free=iter(sorted(set(range(len(new['borders'])))-used))
    moves.extend((entry,next(free)) for entry in unassigned)
    copies=[]
    for entry,stableid in moves:
        previous=entry['id']
        for filename in [f'b{previous}.png',f'world_b{previous}.png']:
            copies.append((filename.replace(str(previous),str(stableid)),(stage/'gfx/interface/APDC/cold_war/map'/filename).read_bytes()))
        entry.update(id=stableid,name=f'b{stableid}',image=f'GFX_APDC_cw_b{stableid}')
        entry['world']['image']=f'GFX_APDC_cw_world_b{stableid}'
    for filename,data in copies:(stage/'gfx/interface/APDC/cold_war/map'/filename).write_bytes(data)
    new['borders'].sort(key=lambda e:e['id']);(out/'geometry.json').write_text(json.dumps(new,separators=(',',':')),'utf-8')
    # Reconstruct only map definitions, leaving every non-map sprite untouched.
    generated=[];prefix='gfx/interface/APDC/cold_war';steps=len(new['palette_ids'])*len(new['scales'])+1
    for kind,entries in [('state',new['pieces']),('border',new['borders'])]:
        for e in entries:
            pad=e['padding'];generated.append(block('progressbartype',f'name = "{e["image"]}"\ntextureFile1 = "{prefix}/map/{e["name"]}.png"\ntextureFile2 = "{prefix}/palette.png"\ncolor = {{ {int(kind=="border")} 0 0 0 }}\nsize = {{ x = {e["w"]+2*pad} y = {e["h"]+2*pad} }}\nsteps = {steps}\neffectFile = "gfx/FX/APDC_cw_palette.shader"'))
            name=e['world']['image'];filename=f'world_{e["id"]}.png' if kind=='state' else f'world_b{e["id"]}.png'
            generated.append(block('spriteType',f'name = "{name}"\ntexturefile = "{prefix}/map/{filename}"\ntransparencecheck = yes\n'+('noOfFrames = 4\n' if kind=='state' else '')))
    generated.append(block('spriteType',f'name = "GFX_APDC_cw_coasts" texturefile = "{prefix}/coasts.png" transparencecheck = yes'))
    (stage/'interface/APDC_cold_war.gfx').write_text(block('spriteTypes',''.join(generated)),'utf-8')
    # Keep unrelated generated content byte exact. Only named map definitions are replaced.
    oldgfx=(real/'interface/APDC_cold_war.gfx').read_text('utf-8')
    newgfx=(stage/'interface/APDC_cold_war.gfx').read_text('utf-8')
    names={e['image'] for e in new['pieces']+new['borders']}|{e['world']['image'] for e in new['pieces']+new['borders']}|{'GFX_APDC_cw_coasts'}
    oldnames={e['image'] for e in old['pieces']+old['borders']}|{e['world']['image'] for e in old['pieces']+old['borders']}|{'GFX_APDC_cw_coasts'}
    bodies=[]
    fills={e['world']['image'] for e in new['pieces']};borders={e['world']['image']:e for e in new['borders']}
    steps=len(new['palette_ids'])*len(new['scales'])+1
    for node in parse(newgfx)[0].children:
        name=node.val('name')
        if name not in names:continue
        body=newgfx[node.start:node.end]
        if name in fills:body=body[:-1]+'effectFile = "gfx/FX/buttonstate_onlydisable.shader"\n}'
        if name in borders:
            entry=borders[name];texture=f'gfx/interface/APDC/cold_war/world_style/border_{entry["id"]}.png'
            n=parse(body)[0].get('texturefile');body=body[:n.value_start]+'"'+texture+'"'+body[n.value_end:]
            body=body[:-1]+'noOfFrames = 2\n}'
        bodies.append(body+'\n')
    for node in parse(oldgfx)[0].children:
        if node.val('name') not in oldnames|names:bodies.append(oldgfx[node.start:node.end]+'\n')
    merged=block('spriteTypes',''.join(bodies));(stage/'interface/APDC_cold_war.gfx').write_text(merged,'utf-8')
    import world_style
    world_style.ROOT=stage
    # This function only updates the staged GFX and map-only style textures.
    world_style.apply_assets()
    # Keep the exact pre-task bytes for unchanged sprite declarations.
    # Native paths use the installed APDC_cw_palette.shader spelling.
    with zipfile.ZipFile(backup.resolve()/'project-before.zip') as archive:
        original_gfx=archive.read('interface/APDC_cold_war.gfx').decode('utf-8-sig')
    staged_gfx=(stage/'interface/APDC_cold_war.gfx').read_text('utf-8');generated_nodes={n.val('name'):n for n in parse(staged_gfx)[0].children};gfx_edits=[]
    for node in parse(original_gfx)[0].children:
        replacement=generated_nodes.get(node.val('name'))
        if replacement is None:gfx_edits.append((node.start,node.end,''))
        elif canonical(node)!=canonical(replacement):gfx_edits.append((node.start,node.end,staged_gfx[replacement.start:replacement.end]))
    for start,end,value in sorted(gfx_edits,reverse=True):original_gfx=original_gfx[:start]+value+original_gfx[end:]
    # State additions create genuinely new map declarations. Existing unrelated
    # sprites remain byte exact; insert only names absent from the original.
    existing_names={n.val('name') for n in parse(original_gfx)[0].children}
    additions=''.join(staged_gfx[n.start:n.end]+'\n' for name,n in generated_nodes.items() if name not in existing_names)
    if additions:
        closing=parse(original_gfx)[0].value_end-1
        original_gfx=original_gfx[:closing]+additions+original_gfx[closing:]
    assert {n.val('name'):canonical(n) for n in parse(original_gfx)[0].children}=={n.val('name'):canonical(n) for n in generated_nodes.values()}
    (stage/'interface/APDC_cold_war.gfx').write_bytes(original_gfx.encode('utf-8'))
    import build_view,build_ui,world_renderer
    build_view.ROOT=stage;build_ui.ROOT=stage;world_renderer.ROOT=stage
    build_view.build();build_ui.build()
    # Assert the generated UI differs solely in the map containers/properties.
    allowed_gui={'apdc_cw_world'}
    gui_old=(real/'interface/APDC_cold_war.gui').read_text('utf-8');gui_new=(stage/'interface/APDC_cold_war.gui').read_text('utf-8')
    oldnodes=parse(gui_old)[0].children;newnodes=parse(gui_new)[0].children
    oldother=[canonical(n) for n in oldnodes if n.val('name') not in allowed_gui]
    newother=[canonical(n) for n in newnodes if n.val('name') not in allowed_gui]
    assert oldother==newother,'Generator would alter unrelated UI; inspect staged output'
    sg_old=parse((real/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8'))[0]
    sg_new=parse((stage/'common/scripted_guis/APDC_cold_war.txt').read_text('utf-8'))[0]
    assert [canonical(n) for n in sg_old.children if n.key!='apdc_cw_world']==[canonical(n) for n in sg_new.children if n.key!='apdc_cw_world']
    # Preserve byte layout of every non-map GUI entry.
    def replace_named(oldtext,newtext,outer,nametest):
        oldroot=parse(oldtext)[0];newroot=parse(newtext)[0]
        olds={nametest(n):n for n in oldroot.children};news={nametest(n):n for n in newroot.children};edits=[]
        for name in outer:
            a=olds[name];b=news[name];edits.append((a.start,a.end,newtext[b.start:b.end]))
        for start,end,value in sorted(edits,reverse=True):oldtext=oldtext[:start]+value+oldtext[end:]
        return oldtext
    (stage/'interface/APDC_cold_war.gui').write_text(replace_named(gui_old,gui_new,allowed_gui,lambda n:n.val('name')),'utf-8')
    p='common/scripted_guis/APDC_cold_war.txt';a=(real/p).read_text('utf-8');b=(stage/p).read_text('utf-8');(stage/p).write_text(replace_named(a,b,allowed_gui,lambda n:n.key),'utf-8')
    # Build_view's non-geometry functions must remain identical.
    view='common/scripted_effects/APDC_cold_war_view.txt';oldview=(real/view).read_text('utf-8');newview=(stage/view).read_text('utf-8')
    allowed_effects={'apdc_cw_initialize_geometry','apdc_cw_ensure_render_lookup','apdc_cw_ensure_world_style_lookup','apdc_cw_refresh_world','apdc_cw_ensure_world_cache','apdc_cw_check_core_map','apdc_cw_prepare_detail'}
    before={n.key:n for n in parse(oldview)};after={n.key:n for n in parse(newview)}
    assert before.keys()==after.keys()
    for name in before:
        if canonical(before[name])!=canonical(after[name]):assert name in allowed_effects,('unrelated view function changed',name)
    # A geometry signature invalidates persisted render lookup and view caches once.
    signature=hashlib.sha256(json.dumps({k:new[k] for k in ['states','pieces','borders']},sort_keys=True).encode()).hexdigest()[:12]
    for oldflag in ['apdc_cw_render_lookup_v2','apdc_cw_world_style_lookup_v1']:
        newview=newview.replace(oldflag,oldflag+'_geo_'+signature)
    newview=newview.replace('apdc_cw_world_cache_version = 4','apdc_cw_world_cache_version = '+str(1000+int(signature[:4],16)))
    (stage/view).write_text(newview,'utf-8')
    output_files=['interface/APDC_cold_war.gfx','interface/APDC_cold_war_world_styles.gfx','interface/APDC_cold_war.gui','common/scripted_guis/APDC_cold_war.txt',view,'common/synchronized_dynamic_tokens/APDC_cold_war.txt','docs/cold-war/20261024/geometry.json']
    # The map-only rebuild must not change localisation or other scripted text.
    for rel in ['common/scripted_localisation/APDC_cold_war_view.txt','common/scripted_localisation/APDC_cold_war.txt']:
        assert (stage/rel).read_bytes()==(real/rel).read_bytes(),('unexpected generated text change',rel)
    loc_rel='localisation/simp_chinese/APDC_cold_war_l_simp_chinese.yml'
    loc_text=(stage/loc_rel).read_text('utf-8-sig');added_loc=[]
    for sid in sorted(set(new['states'])-set(old['states']),key=int):
        line=f' APDC_CW_STATE_{sid}:0 "§Y[{sid}.Owner.GetName]§!"\n'
        assert loc_text.count(line)==1
        loc_text=loc_text.replace(line,'');added_loc.append(line)
    # Earlier additions were appended to preserve every original byte. The
    # full generator sorts them next to older state tooltips. Compare lines
    # without imposing that generated order, then retain original bytes.
    from collections import Counter
    with zipfile.ZipFile(backup.resolve()/'project-before.zip') as archive:
        original_loc=archive.read(loc_rel)
    assert Counter(loc_text.splitlines())==Counter(original_loc.decode('utf-8-sig').splitlines()), 'Only new state country-name tooltips may be added'
    ending=b'\r\n' if b'\r\n' in original_loc else b'\n'
    (stage/loc_rel).write_bytes(original_loc+(ending if not original_loc.endswith(b'\n') else b'')+''.join(added_loc).encode('utf-8').replace(b'\n',ending))
    output_files.append(loc_rel)
    for folder in ['gfx/interface/APDC/cold_war/map','gfx/interface/APDC/cold_war/world_style']:
        output_files.extend(p.relative_to(stage).as_posix() for p in (stage/folder).glob('*.png'))
    output_files.append('gfx/interface/APDC/cold_war/coasts.png')
    # Keep installed world antialiasing whenever the underlying geometry is
    # identical. Rebuilding every tiny mask can otherwise change unrelated
    # edge pixels across Pillow versions or older generation checkpoints.
    import io
    import numpy as np
    from PIL import Image
    preserved_edges=[];prefix='gfx/interface/APDC/cold_war/'
    with zipfile.ZipFile(backup.resolve()/'project-before.zip') as archive:
        archived=set(archive.namelist())
        oldpieces={e['name']:e for e in old['pieces']}
        oldborders={borderkey(e):e for e in old['borders']}
        def preserve(src,dest):
            if src not in archived:return
            data=archive.read(src);target=stage/dest
            if target.read_bytes()!=data:target.write_bytes(data);preserved_edges.append(dest)
        for entry in new['pieces']:
            previous=oldpieces.get(entry['name'])
            if not previous or any(previous[k]!=entry[k] for k in ['x','y','w','h','padding']):continue
            rel=prefix+'map/'+entry['name']+'.png'
            a=np.asarray(Image.open(io.BytesIO(archive.read(rel))))
            b=np.asarray(Image.open(stage/rel))
            if not np.array_equal(a[:,:,0],b[:,:,0]):continue
            preserve(prefix+f'map/world_{previous["id"]}.png',prefix+f'map/world_{entry["id"]}.png')
            preserve(prefix+f'world_style/black_{previous["id"]}.png',prefix+f'world_style/black_{entry["id"]}.png')
        for entry in new['borders']:
            previous=oldborders.get(borderkey(entry))
            if not previous or any(previous[k]!=entry[k] for k in ['x','y','w','h','padding']):continue
            a=np.asarray(Image.open(io.BytesIO(archive.read(prefix+'map/'+previous['name']+'.png'))))
            b=np.asarray(Image.open(stage/prefix/'map'/(entry['name']+'.png')))
            if not np.array_equal(a[:,:,0]==0,b[:,:,0]==0):continue
            preserve(prefix+f'map/world_b{previous["id"]}.png',prefix+f'map/world_b{entry["id"]}.png')
            preserve(prefix+f'world_style/border_{previous["id"]}.png',prefix+f'world_style/border_{entry["id"]}.png')
    # Do not replay another date's installation/rollback report. This run's
    # backup is the sole installation baseline; re-use of staged output is local.
    changed=[]
    for rel in output_files:
        src=stage/rel;dest=real/rel
        if not dest.exists() or src.read_bytes()!=dest.read_bytes():
            changed.append({'file':rel,'before':sha(dest) if dest.exists() else None,'after':sha(src)});dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    installed_this_pass=len(changed)
    manifest_path=backup.resolve()/'manifest-before.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text('utf-8'));changed=[]
        for rel in output_files:
            before=manifest.get(rel,{}).get('sha256');after=sha(real/rel)
            if before!=after:changed.append({'file':rel,'before':before,'after':after})
    # No old unused source is deleted: backups and previous layouts remain traceable.
    report={'signature':signature,'renderer':'native','scales':new['scales'],'palette_unchanged':True,'shader_unchanged':True,'non_map_gui_unchanged':True,'registered_tags_not_in_existing_palette':excluded_palette_tags,'states':len(new['states']),'pieces_before':len(old['pieces']),'pieces_after':len(new['pieces']),'borders_before':len(old['borders']),'borders_after':len(new['borders']),'unchanged_world_edge_assets_preserved':preserved_edges,'installed_this_pass':installed_this_pass,'changed':changed,'stage':str(stage)}
    report_relative='docs/map-maintenance/20261027/cold-war-refresh.json'
    if '--report' in sys.argv:report_relative=sys.argv[sys.argv.index('--report')+1]
    reportpath=real/report_relative;reportpath.parent.mkdir(parents=True,exist_ok=True);reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['changed','unchanged_world_edge_assets_preserved']}));print('changed_files',len(changed));print('preserved_edge_assets',len(preserved_edges))

if __name__=='__main__':run(Path(sys.argv[1]))
