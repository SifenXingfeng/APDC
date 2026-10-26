# 医疗中心模型与建筑

这是根据用户提供的单张医院照片制作的独立静态建筑。保留高塔、低翼楼、白色圆角外框、横向挑檐和蓝灰玻璃幕墙；不含文字、标牌、人物、车辆或环境建筑。背面及屋顶设备是为完整地图模型补全的设计，并非照片中可考证的原建筑背面。

## 当前玩法范围

- ID：`APDC_medical_center`；显示名：医疗中心。
- 地区建筑，每地区上限 1 座，独立容量，不占工厂共享建筑槽。
- 建造费用暂定 6,000，使用正常民用工厂建造流程及基础设施建造修正。
- 隐藏科技 `APDC_medical_center_unlock` 在 `on_startup` 为各国开启。没有额外玩家科研操作，没有 DLC 要求。
- 不预置建筑，不提供人力、人口、损耗、补给、工厂或任何其他加成。
- 不改原有国家历史、工厂初始化、OOB、地图省份颜色或国家所有权。

## 游戏文件

- `common/buildings/APDC_medical_center.txt`：建筑定义。
- `common/technologies/APDC_medical_center.txt`：隐藏建设许可。
- `common/on_actions/APDC_medical_center.txt`：开局开启建设许可。
- `gfx/entities/APDC_medical_center.asset`、`.gfx`：建筑实体与 mesh 映射。
- `gfx/models/buildings/APDC_medical_center/`：标准 Clausewitz `.mesh` 及漫反射、法线、材质参数 DDS。
- `interface/zz_APDC_medical_center.gfx`：建筑图标组追加第 32 帧。前 31 帧逐像素保留。
- `map/buildings.txt`：仅追加医疗中心放置记录，覆盖当前 2,525 个地区。每个中心点都经过省份分色图的所属地区/陆地校验，高度取对应高度图灰度值的 0.1 倍。小岛、微型城市地区的模型边缘可能跨过地区边界；这不改变该建筑所属地区。
- `localisation/english/`、`localisation/simp_chinese/`：中英文名称、说明。

## 模型规格

- 9,814 个三角面，22,697 个导出顶点，1 个静态网格、1 个材质。
- 3 张 1024×1024 DXT5/BC3 DDS，每张包含完整 11 级 mipmap。
- 原始网格尺寸约 5.88 × 3.39 × 6.62（Blender X/Y/Z；导出器转为引擎 Y 向上）。
- 地图实体统一缩放为 `0.30`，实际宽/深/高约 1.76 × 1.02 × 1.98；原版民用工厂约 1.17 × 1.62 × 1.92。只调整地图实体大小，不改网格、贴图、建造图标或建筑效果。
- Shader：原版 `PdxMeshAdvancedSnow`，支持引擎雪覆盖。
- 法线纹理按本机游戏 shader 的 G/X、A/-Y、B/自发光约定制作；无自发光。
- 玻璃使用不透明的颜色与高光表现，避免地图建筑的透明排序问题。
- 未制作独立废墟模型、动画和多级外观；损坏/维修不切换废墟外观。

## 可编辑源文件与重建

`art_source/medical_center/APDC_medical_center.blend` 含网格、UV、已打包材质、灯光和预览相机；同目录保留程序生成的 PNG 贴图源、图标渲染源及验证记录。建模单位先按楼体尺度构建，再统一缩放为地图模型。

构建需要 Blender 4.2、普通 Python + Pillow，以及 [ross-g/io_pdx_mesh](https://github.com/ross-g/io_pdx_mesh) 导出工具。导出器仅作为外部工具使用，不捆绑第三方源码进项目，不使用它的 UI、自动更新或全局用户设置。

1. 用 Blender 后台运行 `build_medical_center.py`，传入 `--exporter`、`--project`、`--delivery`。
2. 用普通 Python 运行 `finish_medical_center.py <交付目录>`，生成 DDS、建筑图标并打包交付源文件。
3. 用 Blender 后台运行 `verify_game_mesh.py`，以最终 `.mesh` 和最终 DDS 重新导入、渲染，验证的不是仅供预览的原始网格。
4. `prepare_map_placements.py <输出JSON>` 只生成放置计划；不会直接改地图，也拒绝重复追加。地图扩展后应先核对计划，再以增量方式合入新增记录。

## 验证边界与游戏内验收

已完成：mesh 二进制导出/读取、独立重新导入、包围盒/UV/法线/切线/索引检查、最终 DDS 回读渲染、图标帧保留检查、地图落点校验，以及原有地图记录保持不变的验证。

初版已由用户提供的游戏截图确认能够建造并显示。随后根据与民用工厂的大小对比，将地图实体等比例缩小至原来的 30%；这一缩放版本尚未在游戏内复核。

建议重启游戏后新开一局，进入建设栏的地区建筑分类，选择“医疗中心”并在自有地区排队建造；完成后确认地区数量为 1、地图模型显示。悬浮说明不应出现增益。若有加载问题，提供本局 `error.log` 中含 `APDC_medical_center` 的行即可；不需要交出鼠标键盘控制。
