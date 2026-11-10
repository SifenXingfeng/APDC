# 62张加载图与第14张主菜单（2026-11-09）

用户输入：`D:/Desktop/加载图定图/1.png` 至 `62.png`，按编号自然顺序使用。原项目26个背景大图全部更换，不保留其旧图片内容。用户在转换到第61张之前修正了该文件，当前62张输入均为1920×1440；修正前的61号仅保留在外部备份的过期资料中。

## 文件与分配

- 1—13、15—28号：依次覆盖27个原版/已安装DLC大图路径，包含此前遗漏的`load_ww`、`load_goe`、`load_ncns_chi`、`load_ncns_jap`、`load_taog_ast`。
- 29—62号：34个新增路径`gfx/loadingscreens/load_apdc_029.dds`至`load_apdc_062.dds`。
- 14号：仅保存为`gfx/loadingscreens/apdc_mainmenu_14.dds`，供默认主菜单使用，不再另存为普通加载图，也不显式登记到背景表。
- 每张大图另有192×144缩略图，全部替换对应原版预览；共62张大图、62张缩略图。
- 22个原有同名覆盖路径写入新图；旧`mainmenu.dds`及`load_bba_2.dds`、`load_botb_2.dds`、`load_dod_2.dds`已删除。旧图片原字节在备份中保留。

主菜单默认与中文默认sprite、通用背景模板均指向同一份14号文件。`common/frontend/backgrounds/base_backgrounds.txt`登记其余61张；新画面不使用原图的DLC筛选条件。未由原生文件提供的缩略图sprite在`interface/APDC_loading_previews.gfx`补齐。

完整编号到路径、源图与DDS哈希见[manifest.json](manifest.json)，便于查看的清单见[mapping.csv](mapping.csv)。维护入口为[导入工具](../../../tools/loading_screens/README.md)。

## 主菜单自动加入加载列表的实证

修改前，原版背景库登记27项，实际用户settings还包含旧`gfx/loadingscreens/mainmenu.dds`。本轮不重复登记14号，最终后台正常退出写出的真实settings中恰好有62条背景路径、62个不同路径，与62张输入映射完全相等；`apdc_mainmenu_14.dds`仅出现一次。旧`mainmenu.dds`不再出现在列表中。证据为`evidence/settings.txt`及[runtime-verification.json](runtime-verification.json)。

## 静态与实际画面验收

全部62张大图使用无压缩BGRA32 DDS，不缩放、不裁剪；逐张通过DDS回读，完整RGBA像素与当前用户PNG一致，62张画面互不相同。全部缩略图也通过回读，配置解析、27原版覆盖路径、61显式登记及无旧新增路径残留均通过。

使用用户当前APDC+Toolpack及DLC设置，在私有桌面完成一次最终加载/主菜单验收：

- [实际加载画面](loading-screen-1920x1080.png)已显示新图。
- [实际主菜单](main-menu-14-1920x1080.png)已确认第14张背景。
- 背景、缩略图及背景配置相关日志错误为零。
- 标题Logo、两处50像素留白、菜单与媒体按钮相对位置、加载条/提示框GUI及受保护地图美术哈希未变。
- 未切换输入桌面、未发送鼠标键盘；向本次自建窗口请求正常关闭后，确认自建进程、助手及Steam运行标记清理完毕。
- 用户原settings、pdx_settings及dlc_load哈希未变。

本次不扩大为地图或战局测试，也不将静态覆盖描述成62张画面逐张游戏轮播或背景选择器手动点击验收。隔离Steam会话仍有物品所有权验证提示，未修改其验证逻辑。

## 备份与输入修正

`D:/C-Drive-Migration-20260929/Permanent/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/.codex_backups/APDC/20261109-225448-loading-images-62`

其中`before/`保留旧运行文件，`inputs/`保存62张当前源图，`superseded-input/`保留修正前61号，`input-revision-61.json`记录其替换时间、尺寸及哈希，`stage/`保留已核验输出。还保存原日志、用户设置与输入/输出清单。不要恢复本次全部备份来回退单独一张图；先按映射确认需恢复的范围。
