"""Auditable compatibility repairs; edits preserve unrelated bytes and data."""
from pathlib import Path
import collections, hashlib, json, re, shutil, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'unit_overhaul'))
from cw import parse,walk,patches
from triage import ROOT,OUT,POINTER
GAME=Path('D:/SteamLibrary/steamapps/common/Hearts of Iron IV')
BACKUP=Path(POINTER.read_text('utf-8').strip())
MANIFEST=OUT/'repairs.json'
changes=json.loads(MANIFEST.read_text('utf-8')) if MANIFEST.exists() else []

def text(rel):
 p=ROOT/rel
 return (p if p.exists() else GAME/rel).read_text('utf-8-sig')

def save(rel,t,reason,bom=None):
 p=ROOT/rel
 before=p.read_bytes() if p.exists() else None
 if bom is None:bom=p.suffix=='.yml'
 data=t.encode('utf-8-sig' if bom else 'utf-8')
 if before==data:return
 dst=BACKUP/'original'/rel
 if before is not None and not dst.exists():
  dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(before)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 changes.append({'path':str(rel).replace('\\','/'),'reason':reason,
  'before':hashlib.sha256(before).hexdigest() if before is not None else None,'after':hashlib.sha256(data).hexdigest()})
 MANIFEST.write_text(json.dumps(changes,ensure_ascii=False,indent=2),'utf-8')

def edit(rel,fn,reason):save(rel,fn(text(rel)),reason)

def delete(rel,reason):
 p=ROOT/rel
 if not p.exists():return
 before=p.read_bytes();dst=BACKUP/'original'/rel
 if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(before)
 p.unlink()
 changes.append({'path':str(rel).replace('\\','/'),'reason':reason,'before':hashlib.sha256(before).hexdigest(),'after':None})
 MANIFEST.write_text(json.dumps(changes,ensure_ascii=False,indent=2),'utf-8')

_bundled_sources=None
def files(folder):
 global _bundled_sources
 excluded=re.findall(r'replace_path\s*=\s*"([^"]+)"',text('descriptor.mod'))
 result={p.relative_to(GAME).as_posix():p for p in (GAME/folder).rglob('*.txt')
         if not any(p.relative_to(GAME).as_posix().startswith(x.rstrip('/')+'/') for x in excluded)}
 if _bundled_sources is None:
  _bundled_sources={}
  for bundle in ['dlc','integrated_dlc']:
   for p in (GAME/bundle).rglob('*.txt'):
    suffix=p.relative_to(GAME/bundle).as_posix().split('/common/',1)
    if len(suffix)==2:_bundled_sources['common/'+suffix[1]]=p
 for rel,p in _bundled_sources.items():
  if rel.startswith(folder.rstrip('/')+'/') and not any(rel.startswith(x.rstrip('/')+'/') for x in excluded):result[rel]=p
 result.update({p.relative_to(ROOT).as_posix():p for p in (ROOT/folder).rglob('*.txt')})
 return result

def own_repairs():
 edit('interface/GFCC_area_gui.gfx',lambda t:t.replace('}c','}'),'Remove accidental token after the sprite definition')
 edit('interface/APDC_super_event.gui',lambda t:re.sub(r'(?i)(orientation\s*=\s*)"?UPPER_LEFT"?',r'\1upper_left',t),'Use the supported orientation spelling')
 edit('common/scripted_localisation/GFCC_area_text.txt',lambda t:re.sub(r'\b(GFCC_area_Pollution_B1)\s*=\s*0',r'NOT = { \1 > 0 }',t),'Building level triggers require a greater-than comparison')
 edit('common/scripted_guis/00_GFCC_area_gui.txt',lambda t:re.sub(r'\bupdate_gui\s*=\s*yes',r'add_to_variable = { global.refresh_gui = 1 }',t),'Replace the missing refresh helper with its dirty-variable update')
 edit('common/decisions/GFCC_area.txt',lambda t:t.replace('allowed = {\n\t\t\tis_debug = yes','visible = {\n\t\t\tis_debug = yes'),'Debug state is a runtime visibility predicate, not an allowed predicate')
 # APDC's low-countries actions already define the identical fifteen-day
 # cooldown under BEL. Keep UI keys while using the established implementation.
 edit('common/scripted_guis/APDC_play_a_game_scripted_guis.txt',lambda t:t.replace('APDC_game_LUX_action_cd_trigger','APDC_game_BEL_action_cd_trigger').replace('APDC_game_LUX_action_cd_effect','APDC_game_BEL_action_cd_effect').replace('LUX = {','LLU = {'),'Repair the missing low-countries action helpers and current APDC target')
 rel='common/decisions/categories/APDC_focus_categories.txt'
 save(rel,'political_actions = { icon = generic_political_actions }\n','Restore the category used by APDC German political decisions')
 # Native event namespaces must be declared with add_namespace and must match
 # the prefix of each event ID; retain existing event IDs and localisation.
 rel='events/SOV_events.txt';t=text(rel)
 namespaces=list(dict.fromkeys(re.findall(r'\bid\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\.\d+',t)))
 t=re.sub(r'^namespace\s*=.*\n',''.join('add_namespace = '+n+'\n' for n in namespaces),t,flags=re.M)
 save(rel,t,'Register the namespaces of the existing Soviet events')
 rel='common/national_focus/SOV_national_focus.txt';t=text(rel);edits=[];aliases={}
 for tree in parse(t):
  if tree.key!='focus_tree':continue
  c=tree.get('country')
  if c:edits.append((c.value_start,c.value_end,'{ factor = 0 modifier = { add = 100 tag = SOV } }'))
  for focus in tree.children:
   if focus.key!='focus':continue
   ident=focus.val('id')
   for key in ['name','desc']:
    n=focus.get(key)
    if n:
     target=ident+('_desc' if key=='desc' else '')
     # Native descriptions already use this key. An alias to itself shadows
     # the authored description and creates a localisation cycle.
     if target != n.value.strip('"'):aliases[target]=n.value
     edits.append((n.start,n.end,''))
   for n in walk(focus.children):
    if n.key=='prerequisite':
     for child in n.children:
      if not child.op:edits.append((child.start,child.end,'focus = '+child.key))
 t=patches(t,edits)
 save(rel,t,'Restrict the Soviet tree to SOV and repair native focus fields and prerequisites')
 if aliases:
  for lang in ['simp_chinese','english']:
   save('localisation/'+lang+'/APDC_focus_compatibility_l_'+lang+'.yml','l_'+lang+':\n'+''.join(' '+k+':0 "'+('$'+v.strip('"')+'$')+'"\n' for k,v in aliases.items()),'Preserve authored focus titles and descriptions through native localisation keys')
 # The authored Soviet focus names a satellite category which was never
 # defined. Use the project's existing puppet rules as its explicit baseline.
 rel='common/autonomous_states/APDC_communist_satellite.txt'
 if not (ROOT/rel).exists():
  t=text('common/autonomous_states/puppet.txt')
  t=t.replace('id = autonomy_puppet','id = autonomy_communist_satellite')
  save(rel,t,'Define the authored satellite relation using the existing puppet baseline')
  for lang in ['simp_chinese','english']:
   save('localisation/'+lang+'/APDC_satellite_l_'+lang+'.yml','l_'+lang+':\n autonomy_communist_satellite:0 "'+('卫星国' if lang=='simp_chinese' else 'Satellite State')+'"\n','Name the existing Soviet focus relation')

if __name__=='__main__':
 own_repairs()
 print('Recorded edits:',len(changes))
