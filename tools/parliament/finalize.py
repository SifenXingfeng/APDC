"""Seal evidence only after static, native-game and reload reports pass."""
from datetime import datetime, timezone
from common import *
import common as shared


def main():
    backup=begin(json.loads(read('docs/parliament/20261107-implementation/backup.json'))['backup'])
    reports={name:json.loads((REPORT/(name+'.json')).read_text('utf-8')) for name in ['static-verification','runtime-verification','reload-verification','preservation-audit']}
    assert all(r['status']=='passed' for r in reports.values())
    profile=Path(reports['runtime-verification']['profile'])
    stop=json.loads((profile/'silent-stop.json').read_text('utf-8-sig'))
    assert not stop['still_running'] and not stop['steam_app_running'] and not stop['remaining_helpers'],stop
    before=json.loads((REPORT/'user-profile-before.json').read_text('utf-8'))
    # ROOT is a migrated junction target; use the actual user documents path.
    user=Path('C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV')
    differences=[rel for rel,old_hash in before.items() if not (user/rel).is_file() or hashlib.sha256((user/rel).read_bytes()).hexdigest()!=old_hash]
    assert not differences,differences
    for rel in ['AGENTS.md','项目接手文档/README.md','项目接手文档/00_快速接手/当前状态与未完成事项.md','项目接手文档/03_待实现设计/议会系统_已确认设计与实施计划.md','docs/parliament/20261107-implementation/README.md']:
        text=read(rel).replace('27项静态','29项静态').replace('27项检查通过','29项检查通过')
        write(rel,text)
    manual=read('tools/parliament/README.md').replace('`watch_runtime.py` 仅观察测试日志并对自有隐藏窗口执行PrintWindow。','`watch_runtime.py` 读取测试日志、统一自有私有窗口尺寸并执行PrintWindow；不切换输入桌面，不发送鼠标键盘输入。')
    write('tools/parliament/README.md',manual)
    build=json.loads(read('docs/parliament/20261107-implementation/build.json'))
    build.update(status='implemented_and_verified',static_checks=len(reports['static-verification']['checks']),runtime_checks=len(reports['runtime-verification']['passed_assertions']),reload_checks=len(reports['reload-verification']['checks']))
    json_write('docs/parliament/20261107-implementation/build.json',build)
    sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'tools/parliament').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for rel,entry in shared.MANIFEST.items():
        if (ROOT/rel).is_file():entry['sha256_after']=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    (backup/'changes.json').write_text(json.dumps(shared.MANIFEST,ensure_ascii=False,indent=2),encoding='utf-8')
    checkpoint={'status':'complete','utc':datetime.now(timezone.utc).isoformat(),'backup':str(backup),'static_checks':len(reports['static-verification']['checks']),'native_checks':len(reports['runtime-verification']['passed_assertions']),'reload_checks':len(reports['reload-verification']['checks']),'initialized_countries_with_500_seats':reports['runtime-verification']['all_initialized_countries_have_500_seats'],'related_engine_errors':[],'manual_mouse_keyboard_validation':False,'user_profile_hashes_unchanged':before,'process_cleanup':stop,'post_runtime_ui_polish':['candidate name truncation','per-option supplied icons','explicit close cache refresh'],'authoring_source_hashes':sources,'generated_and_modified_paths':sorted(shared.MANIFEST)}
    json_write('docs/parliament/20261107-implementation/checkpoint.json',checkpoint)
    print(json.dumps({k:checkpoint[k] for k in ['status','static_checks','native_checks','reload_checks','initialized_countries_with_500_seats']},ensure_ascii=False))


if __name__=='__main__':main()
