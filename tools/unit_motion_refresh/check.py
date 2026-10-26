from common import *
import math
qa=json.loads((WORK/'roundtrip_validation.json').read_text('utf8'));assert qa['status']=='PASS' and len(qa['models'])==12
gait_path=WORK/'gait_revision_validation.json'
if gait_path.exists():
 gait=json.loads(gait_path.read_text('utf8'));assert gait['status']=='PASS' and len(gait['models'])==7
 for row in gait['models']:
  assert sha(STAGE/'gfx/models/units'/row['id']/(row['id']+'_move.anim'))==row['animation_sha256']
for row in qa['models']:
 rel=Path('gfx/models/units')/row['id']/(row['id']+'.mesh');p=STAGE/rel if (STAGE/rel).exists() else ROOT/rel;assert sha(p)==row['mesh_sha256']
 for clip in row['clips']:
  if clip['clip']=='move' and clip['min_knee_plane_projection'] is not None:assert clip['min_knee_plane_projection']>=0
defs={};meshdefs={};activefiles={}
for root in (ROOT,STAGE):
 for p in (root/'gfx/entities').glob('*'):
  if p.suffix in ('.asset','.gfx'):activefiles[p.relative_to(root)]=p
for rel,path in activefiles.items():
 nodes=parse(path.read_text('utf-8-sig'))
 if path.suffix=='.asset':
  for n in nodes:
   if n.key=='entity':assert n.val('name') not in defs,('duplicate entity',n.val('name'));defs[n.val('name')]=n
 else:
  for w in nodes:
   for n in w.children:
    if n.key=='pdxmesh':assert n.val('name') not in meshdefs;meshdefs[n.val('name')]=n
assert defs['apdc_ump_sisters_entity'].val('clone')=='APDC_ump_chibi_entity'
assert 'APDC_r6_ump45_entity' not in defs and 'APDC_r6_ump9_entity' not in defs
for name in ('APDC_r6_tactical_doll_entity','APDC_r6_lyuba_entity','APDC_r6_infantry_entity','APDC_ump_chibi_entity'):
 n=defs[name];assert all(c.val('animation')!='long_idle03' for c in n.children if c.key=='state')
 assert all(not any(x in c.val('name','') for x in ('cigarette','lighter')) for c in n.children if c.key=='attach')
for path in STAGE.rglob('*.mesh'):
 tree=pdx.read_meshfile(str(path))
 for obj in tree.find('object'):
  for mesh in obj.findall('mesh'):
   assert len(mesh.get('p'))//3<65536
   for key in ('diff','n','spec'):
    file=path.parent/mesh.find('material').get(key)[0];assert file.exists() or (ROOT/file.relative_to(STAGE)).exists(),file
save_json(WORK/'static_validation.json',{'status':'PASS','models_roundtripped':12,'active_old_ump_entities':0,'smoking_removed':True,'files_sha256':{p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}})
print('STATIC_PASS',len(list(STAGE.rglob('*.anim'))),'custom_animation_files',flush=True)
