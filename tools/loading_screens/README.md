# 编号加载图导入

当前输入为 `D:/Desktop/加载图定图/1.png` 至 `62.png`，按文件名中的整数排序。

第14张专用于主菜单，路径为 `gfx/loadingscreens/apdc_mainmenu_14.dds`。游戏会将默认主菜单纹理追加进背景列表，因此该图不再显式写入 `common/frontend/backgrounds/base_backgrounds.txt`，也不另存一份普通加载图。

其余图片依次覆盖当前27个原版/DLC大图路径；原版路径用完后，29—62号图片使用34个 `load_apdc_<编号>` 新路径。显式背景表61项，连同引擎加入的主菜单图应为62项。

`import_images.py` 先备份当前运行文件、输入、日志及用户设置，再在外部备份目录完整生成并逐像素验证素材，最后才替换项目内文件。旧图片中仍需覆盖的路径写入新图；不再需要的旧路径删除，原始字节仍保留在备份中。不会修改主菜单GUI、标题Logo或加载条等UI。

大图保存为无压缩BGRA32 DDS，保留原尺寸及全部RGBA像素。每张另配192×144缩略图；缩略图保持比例，必要时留透明边。用户修正第61张后，当前62张源图均为1920×1440。

默认只生成备份和待导入文件：

```powershell
python tools/loading_screens/import_images.py
```

确认本次来源和现场后，执行替换：

```powershell
python tools/loading_screens/import_images.py --apply
```

不要把旧任务的输入目录或备份当作当前授权。程序每轮核对本机原版/DLC大图清单；原版新增路径时先更新映射，再重新导入。

输出映射、哈希及本次验收见 [本轮记录](../../docs/ui/20261109-loading-images/README.md)。背景图任务只核验加载与主菜单，不扩大为地图或战局测试。
