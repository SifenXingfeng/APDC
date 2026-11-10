# 议会编译素材

本目录是议会编译的项目内来源，发布时随整个 `tools/` 目录排除即可。游戏使用 `gfx/interface/APDC/parliament/` 和 `gfx/interface/APDC/economic_systems/` 内的成品。

- `ui/`：用户提供的9张原始PNG，保持原始字节、尺寸和Alpha。
- `economic_systems/`：当前项目使用的10张经济体制图标，按稳定key命名。
- `documents/regimes.docx`：九张政体图标的原始文档。
- `documents/laws.docx`：仅显式使用 `--import-data` 时重新导入的原始法案文档。
- `manifest.json`：各文件SHA-256及来源凭据；其中的历史导入位置不作为编译路径。

统一重建命令为 `python -X utf8 tools/compile.py parliament`。日常法案、政体和候选人配置继续以 `tools/parliament/data/` 为准；不要因为保留了原始Word就自动覆盖人工维护的配置。
