"""Seal UI correction evidence without changing the original implementation report."""
import hashlib
import json
import re
from datetime import datetime, timezone
from PIL import Image
import common as shared


def main():
    root=shared.ROOT;report=root/'docs/parliament/20261107-ui-corrections'
    backup=__import__('pathlib').Path(json.loads((report/'backup.json').read_text())['backup'])
    shared.REPORT=report;shared.begin(backup)
    import verify_ui_corrections
    verify_ui_corrections.run()
    state_log=(report/'runtime/game.log').read_text('utf-8-sig',errors='replace')
    assert 'APDC_UI COMPLETE' in state_log
    assert 'PASS ui_member_appointed' in state_log and 'PASS ui_dismiss_removes_role_and_bonus' in state_log
    assert 'APDC_PARL_QA FAIL' not in state_log
    relevant=[]
    for name in ['error.log','final-entry-error.log']:
        text=(report/'runtime'/name).read_text('utf-8-sig',errors='replace')
        relevant.extend(l for l in text.splitlines() if re.search(r'apdc_parl|parliament|Parent window for APDC_cabinet',l,re.I))
    assert not relevant,relevant
    assert 'APDC_UI_FINAL_ENTRY_CAPTURE' in (report/'runtime/final-entry-game.log').read_text('utf-8-sig')
    images=['main','cabinet_appointed','cabinet_dismissed','law_side','folded','entry_preview']
    for name in images:
        with Image.open(report/'runtime'/(name+'.png')) as image:assert image.size==(1920,1080)
    profile=__import__('pathlib').Path('C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/parliament_ui_20261107')
    stop=json.loads((profile/'silent-stop.json').read_text('utf-8-sig'));process=json.loads((profile/'silent-process.json').read_text('utf-8-sig'))
    assert stop['pid']==process['pid'] and not stop['still_running'] and not stop['remaining_helpers'] and not stop['steam_app_running']
    # Prove the only gameplay-effect change is date presentation arithmetic.
    relative='common/scripted_effects/apdc_parliament_backend.txt'
    original=(backup/'files'/relative).read_text('utf-8-sig');current=shared.read(relative)
    before={n.key:original[n.start:n.end] for n in shared.parse(original)};after={n.key:current[n.start:n.end] for n in shared.parse(current)}
    changed=[k for k in before if re.sub(r'\s+','',before[k])!=re.sub(r'\s+','',after[k])]
    assert changed==['apdc_parl_refresh'],changed
    protected=[p for p,v in shared.MANIFEST.items() if p.startswith(('history/','map/','common/characters/','common/ideologies/','gfx/FX/','gfx/fonts/'))]
    assert not protected,protected
    links=[
        ('项目接手文档/00_快速接手/当前状态与未完成事项.md','2026-11-07议会界面后续修正：按用户九项反馈重做原生背景/输入层级、经济选择器同源复制、中文日期、解除任命底部居中、标题删除、饼图外圈、九党图例和入口对位。19项界面专项检查及实际任命/解除回归通过；真实鼠标拖拽/逐点命中仍未人工点验。详见[界面修正记录](../../docs/parliament/20261107-ui-corrections/README.md)。'),
        ('docs/parliament/20261107-implementation/README.md','后续界面以[九项UI修正记录](../20261107-ui-corrections/README.md)为准，原生输入配置、经济选择器和入口对位已进一步修正。'),
    ]
    for rel,paragraph in links:
        text=shared.read(rel)
        if paragraph not in text:
            first,rest=text.split('\n',1);shared.write(rel,first+'\n\n'+paragraph+'\n'+rest)
    rel='tools/parliament/README.md';text=shared.read(rel)
    paragraph='2026-11-07后续UI修正：法案选项行与侧栏直接读取经济系统GUI；不要再手工另写近似布局。窗口使用原生背景、被动文字使用 alwaystransparent，列表与对应按钮共用父GUI上下文。入口按政治页原图y=44对位，讲台点击框取当前素材实际尺寸。证据见[九项修正记录](../../docs/parliament/20261107-ui-corrections/README.md)。'
    if paragraph not in text:
        first,rest=text.split('\n',1);shared.write(rel,first+'\n\n'+paragraph+'\n'+rest)
    record={'status':'implemented','utc':datetime.now(timezone.utc).isoformat(),'static_ui_checks':19,'base_static_checks':29,'native_backend_checks':['ui_member_appointed','ui_dismiss_removes_role_and_bonus'],'new_related_engine_errors':relevant,'observed_images':images,'entry_picture_scope':'native QA composition using actual political background and actual entry/role components','real_mouse_drag_hover_click_wheel_verified':False,'private_window_message_attempt_counted_as_pass':False,'changed_gameplay_effects':changed,'protected_gameplay_paths_changed':protected,'process_cleanup':stop,'backup':str(backup)}
    shared.json_write('docs/parliament/20261107-ui-corrections/checkpoint.json',record)
    for rel,entry in shared.MANIFEST.items():
        if (root/rel).is_file():entry['sha256_after']=hashlib.sha256((root/rel).read_bytes()).hexdigest()
    (backup/'changes.json').write_text(json.dumps(shared.MANIFEST,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
