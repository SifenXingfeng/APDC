"""Read actual isolated-game save data; definition loading alone is not acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,shutil
from cw import TOKEN,parse,walk
from build_core import ROOT,WORK
from catalog import UNIT_IDS,EQUIPMENT_NAMES

QA=Path('D:/APDC_UnitQA_20260915')

def block(text,pattern,start=0):
    match=re.compile(pattern,re.M).search(text,start)
    if not match:raise ValueError('Missing save block: '+pattern)
    opening=text.index('{',match.start());depth=0
    for t in TOKEN.finditer(text,opening):
        if t.group()=='{':depth+=1
        elif t.group()=='}':
            depth-=1
            if depth==0:return text[match.start():t.end()]
    raise ValueError('Unclosed save block')

def read_save():
    path=QA/'save games/autosave.hoi4'
    text=path.read_text('utf-8-sig')
    templates=parse(block(text,r'^division_templates=\{'))[0].children
    countries=re.search(r'^countries=\{',text,re.M).start()
    ger=parse(block(text,r'^\tGER=\{',countries))[0]
    return path,text,templates,ger

def main():
    args=argparse.ArgumentParser()
    args.add_argument('--inspect',action='store_true')
    args.add_argument('--run',default='run4')
    opt=args.parse_args()
    path,text,templates,ger=read_save()
    if opt.inspect:
        print('GER keys:',[(n.key,len(n.children)) for n in ger.children])
        for n in ger.children:
            if any(k in n.key for k in ('production','technology','equipment')):
                print(n.key,[(c.key,len(c.children),c.value) for c in n.children[:12]])
        return
    units=json.loads((WORK/'normalized_units.json').read_text('utf8'))
    errors=[];verified=[]
    for u in units:
        name='列装测试 '+u['name']
        matching=[t for t in templates if t.key=='division_template' and t.val('name')==name and t.val('country')=='GER']
        part='regiments' if u['index']<=49 else 'support' if u['index']<=74 else 'regimental_support'
        good=[t for t in matching if t.get(part) and t.get(part).get(u['id'])]
        if not good:errors.append('Unit absent from actual saved template: '+u['id'])
        else:verified.append({'id':u['id'],'name':u['name'],'section':part})
    logs=QA/'logs'
    game=(logs/'game.log').read_text('utf8',errors='replace')
    error=(logs/'error.log').read_text('utf8',errors='replace')
    system=(logs/'system.log').read_text('utf8',errors='replace')
    stock=sorted(set(re.findall(r'APDC_QA EQUIPMENT_OK (apdc_\w+_equipment)',game)))
    if len(stock)!=31:errors.append('Not all equipment stock checks passed')
    if 'APDC_QA DIVISIONS_82_OK' not in game:errors.append('82 fixture divisions not confirmed')
    if 'APDC_QA PRODUCTION_REQUESTS_31_DONE' not in game:errors.append('Production queue requests incomplete')
    relevant=re.compile(r'apdc_(?:combat|divisional_support|regimental_support|land_|basic_template|unit_|qa|eq_|.*_equipment)|APDC_v5_|APDC_b2_|APDC_f1_|APDC_r6_|zzz_APDC_unit|zz_APDC_unit|category_apdc',re.I)
    own_errors=[line for line in error.splitlines() if relevant.search(line)]
    if own_errors:errors.append('New-content errors in engine log')
    report={
        'status':'PASS' if not errors else 'FAIL','errors':errors,
        'audit_utc':datetime.now(timezone.utc).isoformat(),'game_version':'1.19.2',
        'profile':str(QA),'save':str(path),'save_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'save_modified_utc':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),
        'save_date':re.search(r'^date="([^"]+)"',text,re.M).group(1),
        'template_unit_types_verified':len(verified),'template_units':verified,
        'new_equipment_stock_checks':stock,'production_queue_requests':31,
        'new_content_error_lines':own_errors,
        'other_project_log_errors_remain':bool(error.strip()),
        'active_dlc_log':[l for l in system.splitlines() if 'Active DLC' in l],
        'visual_animation_performance_accepted':False,
        'notes':['QA mod spawns fixtures only in the isolated profile; it is not installed in APDC.',
                 'QA clock is accelerated, without altering combat or economy constants.',
                 'Production queue requests are not a claim that every equipment type completed manufacture.',
                 'DLC-specific user interface has not been visually verified.']}
    archive=WORK/'runtime'/opt.run;archive.mkdir(parents=True,exist_ok=True)
    for name in ('game.log','error.log','system.log','setup.log'):
        if (logs/name).exists():shutil.copy2(logs/name,archive/name)
    (WORK/'runtime_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:report[k] for k in ('status','errors','save_date','template_unit_types_verified','production_queue_requests','new_content_error_lines')},ensure_ascii=False))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
