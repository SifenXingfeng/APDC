"""Package renderer frames without modifying their contents."""
from common import *
from PIL import Image
labels={'APDC_ump_chibi':'UMP姐妹_四肢狂奔_修订','APDC_b2_multipod':'多足机械_交替步态_修订','APDC_b2_aa02':'AA02_前进步态_修订'}
for row in json.loads((WORK/'previews/gait_revision_frames.json').read_text('utf8')):
    frames=[Image.open(path).convert('RGB') for path in row['frames']]
    output=WORK/'previews'/(labels[row['id']]+'.gif')
    frames[0].save(output,save_all=True,append_images=frames[1:],duration=row['duration_ms'],loop=0,optimize=False)
    print(output)
