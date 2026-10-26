from common import *
from PIL import Image
out=WORK/'previews'
for ident,label in [('APDC_ump_chibi','UMP姐妹_骑乘移动'),('APDC_b2_aa02','AA02_膝盖与移动')]:
 frames=[Image.open(p).convert('RGB') for p in sorted((out/'frames'/ident).glob('*.png'))]
 assert len(frames)==15
 frames[0].save(out/(label+'.gif'),save_all=True,append_images=frames[1:],duration=67,loop=0,optimize=False)
# Keep the human-readable model inventory in sync with the new active alias.
path=ROOT/'art_source/unit_overhaul/unit_model_mapping.json'
rows=json.loads(path.read_text('utf8'))
for row in rows:
 if row['unit']=='apdc_ump_sisters':row['model']='ump_chibi'
save_json(path,rows)
print('MOTION_PREVIEWS_READY')
