# 主菜单标题替换（2026-11-09）

本页记录首次 448×175 导入；同日后续已按用户新图改为 896×350，并调整主菜单布局。当前版本见 [主菜单布局](../20261109-main-menu-layout/README.md)。以下为首次修改的历史证据。

按用户提供的 `D:/Desktop/标题.png` 替换主菜单钢铁雄心 IV 标题。

- 运行素材：`gfx/interface/logo_game.dds`。原项目未覆盖此文件；本次新增同路径贴图，覆盖原版标题。
- 原图、原版标题及新贴图均为 448×175；无缩放、无裁剪，保留完整透明度。
- 格式为无压缩 32 位 BGRA DDS。回读全部 RGBA 像素，与用户 PNG 完全一致。
- 现有 `interface/frontendmainview.gui` 的 `GFX_frontend_game_logo` 使用原版 `interface/frontendmainview.gfx` 定义，直接引用该贴图；位置仍为 x=20、y=20。无需新增 sprite 或修改 GUI。
- 只新增此运行贴图，描述文件、界面布局和其他美术未修改。
- 本轮为素材替换，完成尺寸、引用及像素核验；未启动游戏，不将静态核验描述为实机画面验收。

备份及输入：`C:/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/.codex_backups/APDC/20261109-161530-main-menu-title`，包含用户原图、原版回退贴图、替换结果、上下文文件及 `verification.json`。恢复原版标题可移除此轮新增的 DDS。

源 PNG SHA-256：`23a01edb0c3edef1c3ac03958b5dc48c5b67faeac15a201bbc5fa4f1a3e552d7`

输出 DDS SHA-256：`c040fe2b7b2354d0467fe1e74d5fc3c3e11b7741951e92ab7197874c951b8a8c`
