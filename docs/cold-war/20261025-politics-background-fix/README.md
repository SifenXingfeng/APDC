# 政治页面实际背景路径修正（2026-10-25）

前一次只设置 GUI 的新 Sprite/PNG 引用，没有替换仍为旧图的原生 DDS。本次将政治主体恢复为原生 GFX_pol_view_bg，并替换其 gfx/interface/pol_view_bg.dds；无 DLC 原生变体 pol_view_bg_no_dlc.dds 同样使用用户图，避免切换原生变体后恢复旧背景。当前用户启用全部 DLC。

两个 DDS 均由项目内保留的用户 PNG 生成，550×636、未压缩 BGRA、保留 Alpha，解码后与桌面原图逐像素一致。entry_assets.py 已同步生成这些实际路径，重复生成哈希不变。入口素材、坐标、命中范围及原生悬浮/按下效果保持不变，旧顶部入口未恢复。

外部 APDC.mod 指向 C 盘目录，该目录为当前 D 盘工作区的 junction；实际启用的另一模组 Toolpack 未覆盖这些背景路径或 Sprite。本次核对了实际加载路径、DDS 像素、透明度、界面解析和生成器稳定性。actual-background.png 是从实际 DDS 解码的图片；本次没有启动游戏，也不将其称为政治页面实机截图。
