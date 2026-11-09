# 合作组织投票区点击与滚动

用户要求：赞成、弃权、反对三个投票区的任意空白位置均可修改投票；国家超出区域时不显示滚动条，仍可使用滚轮滚动。

## 改动

- 保留原有三个 152×112 投票背景按钮、国家旗帜、计数、列表布局及投票结算效果。
- 原按钮上方覆盖着 148×78 的国家列表窗口。三个列表窗口各自的背景现绑定同一投票动作，让列表空白处有自己的点击入口，同时保持滚轮事件在滚动窗口中处理。
- 三个投票背景图关闭按透明度裁剪点击范围，点击范围覆盖完整矩形。
- 仅三个投票列表改用专用滚动条。控制器、尺寸、贴图九宫格参数和滚轮步长沿用原生实现；背景、滑块、轨道、上下箭头换为完全透明的同尺寸贴图，并穿透鼠标点击。
- 外交成员侧栏、组织成员列表、法案队列及下方的法案列表继续使用原来的可见滚动条。

## 文件

- `interface/APDC_cooperation_organizations.gui`
- `interface/APDC_cooperation_organizations.gfx`
- `common/scripted_guis/APDC_cooperation_organizations_scripted_gui.txt`
- `interface/APDC_cooperation_vote_input.gfx`
- `gfx/interface/APDC/cooperation_organizations/legislation/vote_input/`

## 验证与边界

`static-audit.json` 保存语法、回调绑定、输入区域和透明贴图检查；与本轮备份按语法树对照，确认既有投票效果、旗帜位置和其他窗口未改动。`manifest-after.json` 保存十个运行文件的哈希。

静态检查不能代替游戏内鼠标点验。后台加载测试的最终结果另见 `runtime-audit.json`。

后台测试已完成 GER 2060 战局加载，测试脚本为三个投票列表各填入 12 个国家，超过每区的可视容量。未发现合作组织、脚本 GUI、新增滚动条或点击贴图的相关读取错误。测试进程及其日志查看器均已关闭。未直接操作鼠标，因此点击、滚轮交互及最终画面仍未实机点验。

备份位于主项目同级目录：`.codex_backups/APDC/20261026-201909-cooperation-vote-input`。
