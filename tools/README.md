# APDC 开发工具与统一入口

编译、生成和检查统一从本目录的 `compile.py` 运行，不再为每个新编译器建立独立入口目录。系统子目录保留实现模块、配置、稳定ID和维护资料；它们由统一入口调度。新增编译任务登记在 `compile.py` 的 `TARGETS` 中。

候选人、全部冷战行动、合作组织规则及特殊法案直接维护原生文件，不运行编译器。制作说明与可复制模板见 [原生内容接口](native_content.md)。`native-content-check` 是可选只读检查，`native-content-qa` 只准备/核验私有测试，不会启动游戏。

在项目根目录执行：

```text
python -X utf8 tools/compile.py --list
python -X utf8 tools/compile.py native-content-check
python -X utf8 tools/compile.py parliament
python -X utf8 tools/compile.py parliament-check
python -X utf8 tools/compile.py parliament-ui-check
python -X utf8 tools/compile.py parliament-bills-check
python -X utf8 tools/compile.py cold-war
python -X utf8 tools/compile.py economy-backend
```

任务名后面的参数原样传给相应实现。议会支持 `--backup <目录>`、`--assets-only`、`--import-data`、`--game-dir <游戏安装目录>`。`economy` 等旧生成任务仍须先核查各自的输入和副作用，统一入口不会自动执行其他系统或启动游戏。

新增特殊法案按[原生内容说明](parliament/special_bills.md)直接写游戏脚本，无须执行编译任务。`parliament-bills-check` 仅为可选的只读检查；`parliament-bills-qa` 只准备或核验隔离测试，不会启动游戏。

议会的全部自定义美术原件、经济体制图标和可选导入Word保存在 `tools/assets/parliament/`；重建只读这里的项目文件，不访问桌面。原件的SHA-256和导入凭据见该目录的 `manifest.json`。修改原始法案Word后，只有明确使用 `--import-data` 才会重新导入已有配置。

开发机运行议会编译需要Python、Pillow、lxml和游戏本体素材。议会可通过 `--game-dir` 或 `APDC_GAME_DIR` 指定本体安装目录。游戏运行只读已经生成到 `common/`、`events/`、`interface/`、`gfx/`、`history/`、`localisation/` 等目录的成品，不执行本目录的Python。

发布创意工坊时可以整体排除 `tools/`；应保留所有游戏运行成品。该约定不表示可以删除开发仓库中的工具、配置、稳定ID或地图权威基线。
