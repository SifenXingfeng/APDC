"""Explicit country/palette protocol migration, separate from map-only refresh.

Usage: python tools/cold_war/refresh_palette.py BACKUP COUNTRY_PLAN REPORT
Retains old palette slot numbers, including retired slots; appends new IDs.
Updates matching palette/sector/swatch/GFX-step/shader/view data atomically after
staged checks. Does not regenerate map masks, map quads, UI or input regions.
"""
from pathlib import Path
import sys,json,copy,re,hashlib,shutil,io,math
sys.dont_write_bytecode=True
from PIL import Image
from common import ROOT,GAME,parse
from cw import patches

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(n):return(n.key,n.value,n.op,tuple(canon(x) for x in n.children))
def country_registry():
 files={p.name:p for p in (GAME/'common/country_tags').glob('*.txt')};files.update({p.name:p for p in (ROOT/'common/country_tags').glob('*.txt')})
 out={}
 for p in files.values():
  for n in parse(p.read_text('utf-8-sig')):
   if n.value and n.op=='=':out[n.key]=n.value.strip('"')
 return out
def run(backup,plan_path,report_path):
 backup=backup.resolve();plan=json.loads(plan_path.read_text('utf-8'));stage=backup/'cold-war-palette-stage';stage.mkdir(exist_ok=True)
 for rel in ['history/states','common/country_tags','common/countries','common/ideas']:shutil.copytree(ROOT/rel,stage/rel,dirs_exist_ok=True)
 for rel in ['tools/cold_war/laws.json','tools/cold_war/render_mode.json']:
  p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
 old=json.loads((ROOT/'docs/cold-war/20261024/geometry.json').read_text('utf-8'));new=copy.deepcopy(old);registry=country_registry();new['registry']=registry
 statefiles={}
 for p in (ROOT/'history/states').glob('*.txt'):
  state=parse(p.read_text('utf-8-sig'))[0];sid=state.val('id');assert sid not in statefiles;statefiles[sid]=state
 assert statefiles.keys()==new['states'].keys()
 for sid,state in statefiles.items():new['states'][sid]['owner']=state.get('history').val('owner')
 added=[]
 for tag in sorted(set(plan)-set(old['palette_ids'])):
  file=ROOT/'common'/registry[tag]
  if not file.exists():file=GAME/'common'/registry[tag]
  text=file.read_text('utf-8-sig');m=re.search(r'\bcolor\s*=\s*(?:rgb\s*)?\{\s*(\d+)\s+(\d+)\s+(\d+)',text)
  assert m,('New tag needs a concrete RGB color',tag,file)
  new['palette_ids'][tag]=len(new['palette_ids'])+1;new['colors'][tag]=[int(m[i]) for i in [1,2,3]];added.append(tag)
 for tag,d in plan.items():assert tag in registry;new['colors'][tag]=d['rgb']
 assert all(new['palette_ids'][k]==v for k,v in old['palette_ids'].items())
 assert all(new['colors'][k]==v for k,v in old['colors'].items() if k not in plan)
 assert new['pieces']==old['pieces'] and new['borders']==old['borders'] and new['scales']==old['scales']
 count=len(new['palette_ids']);oldcount=len(old['palette_ids']);steps=count*len(new['scales'])+1;oldsteps=oldcount*len(old['scales'])+1
 assert math.ceil(count/32)==math.ceil(oldcount/32), 'Adding a new pie atlas group also needs a scripted-localisation group migration'
 target=stage/'gfx/interface/APDC/cold_war';target.mkdir(parents=True,exist_ok=True);tags=sorted(new['palette_ids'],key=new['palette_ids'].get)
 palette=Image.new('RGBA',(count,1));palette.putdata([tuple(new['colors'][tag])+(255,) for tag in tags]);palette.save(target/'palette.png')
 swatches=Image.new('RGBA',(16*count,16))
 for i,tag in enumerate(tags):swatches.paste(tuple(new['colors'][tag])+(255,),(16*i,0,16*(i+1),16))
 swatches.save(target/'swatches.png')
 source_art=ROOT/'gfx/interface/APDC/cold_war';template=Image.open(source_art/'pie_0.png').convert('RGBA').crop((0,0,256,256)).getchannel('A');atlas_files=[];unchanged_frames=0
 for group in range(math.ceil(count/32)):
  start=group*32;subset=tags[start:start+32];oldimg=Image.open(source_art/f'pie_{group}.png').convert('RGBA');atlas=Image.new('RGBA',(len(subset)*256,256));atlas.paste(oldimg,(0,0))
  touched=atlas.size!=oldimg.size
  for j,tag in enumerate(subset):
   if tag not in old['palette_ids'] or new['colors'][tag]!=old['colors'][tag]:
    tile=Image.new('RGBA',(256,256),tuple(new['colors'][tag])+(255,));tile.putalpha(template);atlas.paste(tile,(j*256,0));touched=True
   else:
    assert atlas.crop((j*256,0,(j+1)*256,256)).tobytes()==oldimg.crop((j*256,0,(j+1)*256,256)).tobytes();unchanged_frames+=1
  if touched:atlas.save(target/f'pie_{group}.png');atlas_files.append(f'gfx/interface/APDC/cold_war/pie_{group}.png')
 gfx_rel='interface/APDC_cold_war.gfx';text=(ROOT/gfx_rel).read_text('utf-8');nodes=parse(text)[0].children;edits=[]
 for n in nodes:
  if n.key=='progressbartype':
   step=n.get('steps');assert step and int(step.value)==oldsteps;edits.append((step.value_start,step.value_end,str(steps)))
  name=n.val('name')
  if name=='GFX_APDC_cw_swatches':
   frame=n.get('noOfFrames');edits.append((frame.value_start,frame.value_end,str(count)))
  if name and re.fullmatch(r'GFX_APDC_cw_pie_\d+',name):
   i=int(name.rsplit('_',1)[1]);frame=n.get('noOfFrames');newframes=min(32,count-i*32)
   if int(frame.value)!=newframes:edits.append((frame.value_start,frame.value_end,str(newframes)))
 p=stage/gfx_rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(patches(text,edits),'utf-8')
 shader_rel='gfx/FX/APDC_cw_palette.shader';shader=(ROOT/shader_rel).read_text('utf-8');newshader=re.sub(r'\b'+str(oldsteps)+r'\.f\b',str(steps)+'.f',shader);newshader=re.sub(r'\b'+str(oldcount)+r'\.f\b',str(count)+'.f',newshader)
 assert shader!=newshader and str(steps)+'.f' in newshader and str(count)+'.f' in newshader
 p=stage/shader_rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(newshader,'utf-8')
 meta_rel='docs/cold-war/20261024/geometry.json';p=stage/meta_rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(new,separators=(',',':')),'utf-8')
 # Generate data only, then merge allowed functions back into the current file.
 import common
 common.ROOT=stage;common.OUT=stage/'docs/cold-war/20261024'
 import build_view,world_renderer
 build_view.ROOT=stage;world_renderer.ROOT=stage;build_view.build()
 effect_rel='common/scripted_effects/APDC_cold_war_view.txt';original=(ROOT/effect_rel).read_text('utf-8');generated=(stage/effect_rel).read_text('utf-8');a={n.key:n for n in parse(original)};b={n.key:n for n in parse(generated)};assert a.keys()==b.keys()
 signature=hashlib.sha256(json.dumps({'palette':new['palette_ids'],'colors':new['colors'],'owners':{k:v['owner'] for k,v in new['states'].items()}},sort_keys=True).encode()).hexdigest()[:12]
 flag='apdc_cw_palette_v_'+signature
 init=b['apdc_cw_initialize_geometry'];generated=generated[:init.value_end-1]+'set_global_flag = '+flag+'\n'+generated[init.value_end-1:]
 b={n.key:n for n in parse(generated)};ensure=b['apdc_cw_ensure_render_lookup'];header='if = { limit = { NOT = { has_global_flag = '+flag+' } } apdc_cw_initialize_geometry = yes }\n'
 generated=generated[:ensure.value_start+1]+header+generated[ensure.value_start+1:]
 generated=generated.replace('apdc_cw_render_lookup_v2','apdc_cw_render_lookup_v2_pal_'+signature).replace('apdc_cw_world_style_lookup_v1','apdc_cw_world_style_lookup_v1_pal_'+signature).replace('apdc_cw_world_cache_version = 4','apdc_cw_world_cache_version = '+str(200000+int(signature[:4],16)))
 b={n.key:n for n in parse(generated)};allowed={'apdc_cw_initialize_geometry','apdc_cw_ensure_render_lookup','apdc_cw_ensure_world_style_lookup','apdc_cw_refresh_world','apdc_cw_ensure_world_cache','apdc_cw_prepare_detail'};effect_edits=[];changed_functions=[]
 for name,oldnode in a.items():
  if canon(oldnode)!=canon(b[name]):
   if name=='apdc_cw_refresh_view':
    # Frame packing uses palette count here too. Preserve all other UI logic.
    oldbody=original[oldnode.start:oldnode.end]
    expected=oldbody.replace('apdc_cw_detail_frame = '+str(oldcount)+' }','apdc_cw_detail_frame = '+str(count)+' }').replace('apdc_cw_border_frame = '+str(oldcount)+' }','apdc_cw_border_frame = '+str(count)+' }')
    assert canon(parse(expected)[0])==canon(b[name]),'Unrelated refresh_view drift'
   else:assert name in allowed,('Non-palette function would change',name)
   effect_edits.append((oldnode.start,oldnode.end,generated[b[name].start:b[name].end]));changed_functions.append(name)
 (stage/effect_rel).write_text(patches(original,effect_edits),'utf-8')
 for rel in ['common/scripted_localisation/APDC_cold_war_view.txt','common/synchronized_dynamic_tokens/APDC_cold_war.txt']:
  assert (stage/rel).read_bytes()==(ROOT/rel).read_bytes(),('Unexpected text/token change',rel)
 outputs=['gfx/interface/APDC/cold_war/palette.png','gfx/interface/APDC/cold_war/swatches.png',gfx_rel,shader_rel,meta_rel,effect_rel]+atlas_files;changed=[]
 for rel in outputs:
  p=ROOT/rel;q=stage/rel
  if not p.exists() or p.read_bytes()!=q.read_bytes():changed.append({'file':rel,'before':sha(p) if p.exists() else None,'after':sha(q)});p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,p)
 report={'signature':signature,'old_palette_count':oldcount,'new_palette_count':count,'appended_tags':added,'existing_slot_indices_unchanged':True,'retired_slots_retained_for_protocol':sorted(set(old['palette_ids'])-set(registry)),'unrelated_registered_tags_without_palette_preserved':sorted(set(registry)-set(new['palette_ids'])),'target_colors':{tag:d['rgb'] for tag,d in plan.items()},'all_other_existing_palette_rgb_unchanged':True,'unmodified_pie_frames_pixel_exact':unchanged_frames,'scales_and_state_border_geometry_unchanged':True,'map_masks_and_nonmap_ui_not_regenerated':True,'old_steps':oldsteps,'new_steps':steps,'palette_shader_gfx_encoding_updated_together':True,'changed_view_functions':changed_functions,'changed':changed,'stage':str(stage)}
 report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['retired_slots_retained_for_protocol','changed']},ensure_ascii=False));print('files changed',len(changed))

if __name__=='__main__':run(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
