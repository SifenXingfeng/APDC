# 主菜单标题与布局（2026-11-09）

后续纠正：本页截图中的订阅状态媒体按钮比原相对位置高 62 像素；本页保留当时证据，不再作为媒体相对位置验收。当前修复与修改前/修改后实机对照见 [媒体按钮偏移修正](../20261109-main-menu-media-offset/README.md)。标题尺寸及两处 50 像素留白继续有效。

当前用户最终要求：使用新版 `D:/Desktop/标题.png`，不缩小标题；标题顶部与标题下方至菜单框的留白均为 50 像素；媒体按钮与菜单一起移动。此记录取代同日首次标题导入的当前状态，首次记录保留为历史证据。

## 运行改动

- `gfx/interface/logo_game.dds`：896×350 原尺寸，无裁剪或缩放，无压缩 32 位 BGRA DDS；逐像素回读与用户 PNG 的完整 RGBA 相同。
- `interface/frontendmainview.gui`：标题父容器以 `center_up` 对齐和定位，动画结束后图像顶部 Y=50；标题底部 Y=400。1920 像素宽时图像左侧 X=512，横向中心为 960。
- 主菜单选项及背景框由同一容器统一定位在 Y=450，距标题底部 50 像素。普通 450 像素高背景框底部 Y=900；引擎启用订阅区时 575 像素高背景框底部 Y=1025，均在 1080 像素视口内。
- 单人游戏子菜单采用相同顶部与横向锚点，防止回到旧屏幕中心覆盖标题。
- 首页、论坛、Discord、隐私政策、Bluesky、X、Facebook、Instagram、YouTube 两排媒体按钮随其父容器整体移动。保留每个按钮原有坐标、大小、缩放、图标、链接、提示与动作。普通/订阅、社交面板启用/禁用的四种父级位置一起适配。
- 主菜单按钮、提示、订阅控件、版本文字和背景框内部布局不变；背景画、右上角标识与地图美术不变。

## 验证

静态完成：GUI 解析通过；标题与 PNG 像素完全一致；四个相关顶层容器之外的 GUI 节点未变；主菜单所有子控件及两排媒体按钮内部定义未变；受保护贴图和描述文件哈希未变。

实际画面通过：以用户当前 APDC + Toolpack 启用组合及当前 DLC 设置，在私有桌面运行一次最终 50 像素版本，1920×1080 主菜单已确认标题原尺寸居中、上方留白、菜单间距，以及两排媒体按钮和订阅背景框完整显示。截图见 [实际主菜单](main-menu-1920x1080.png)。未发送鼠标或键盘输入，不把本次截图描述为按钮点击或完整战局验证。

本次日志中与 `frontendmainview.gui`、`logo_game.dds` 或 GUI 解析相关的错误为零。隔离会话右下角出现 Steam 无法验证物品所有权的提示，属于本次隔离启动的另项提示，未改动其验证逻辑，也不将其描述为已修复。

自建测试进程、助手及 Steam 运行标记均已清理；用户原 settings、pdx_settings 和 dlc_load 与备份哈希一致。证据见 `evidence/visual-verification.json` 及 `silent-stop.json`。

## 证据与恢复

本轮原始现场、源图、SHA-256、旧日志、两版静态结果与临时 100 像素方案的截图：

`C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/.codex_backups/APDC/20261109-173015-main-menu-layout`

`before/interface/frontendmainview.gui` 和 `before/gfx/interface/logo_game.dds` 是本轮修改前的实际项目文件；恢复时同时使用这两份，不用原版 GUI 替换项目现场。

后台验证使用隔离目录：`C:/Users/ASUS/.codex/tmp/APDC_CountryQA_20261028_final/frontend_20261109`。
