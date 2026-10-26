# 马达加斯加墨镜企鹅步兵

根据《马达加斯加的企鹅》的角色外形重新制作的游戏模型，以队长 Skipper 较敦实的轮廓为参考，加入立体墨镜、橙色宽喙、黑白羽色、鳍状手臂和短脚。不是提取的电影原始模型。

## 参考资料

先收集并查看参考，再建模和绑定：

- [梦工厂电影官方页面](https://www.dreamworks.com/movies/penguins-of-madagascar)：确认电影版角色造型。
- [官方四只企鹅全身图](https://www.dreamworks.com/storage/movies/penguins-of-madagascar/penguins-of-madagascar-hero-image.jpg)：轮廓、黑白分区、喙和脚的参考。
- [墨镜造型参考](https://clipground.com/images/skipper-png-9.png)：侧前方眼镜位置和结构；第三方展示图，不视为官方模型文件。
- [io_pdx_mesh](https://github.com/ross-g/io_pdx_mesh)：Clausewitz 网格/骨骼/动作的导入导出工具。

参考图片保存在桌面交付目录的“参考资料”中，不作为游戏贴图使用，也未复制进项目。

## 接入范围

- 仅新增马达加斯加 `MAD` 的步兵模型实体，不覆盖任何原版或其他国家实体。
- 覆盖普通步兵三个装备外观阶段，以及对应沙漠、雪地变体，共 9 个实体。
- 步枪、冲锋枪等武器及其枪口特效、音效沿用原版；人物外形使用同一只企鹅。
- 不改步兵参数、科技、国旗、国家历史或开局军队，不新增额外兵种。
- 不替换坦克、火炮、骑兵载具等其他模型，也不强制覆盖玩家手动指定的其他皮肤。

## 骨架和动作适配

保留原版德国步兵的 33 个骨骼/挂点名称、顺序和父子层级。由于原始人形长腿会使企鹅蹲下时脚穿进腹部，不能仅把宽大的企鹅身体硬套到完全不变的人形比例上。

当前进行了以下企鹅专用适配：

1. 降低骨盆、髋部及膝部的绑定位置，缩短隐藏在羽毛下的腿；脚的绑定位置保留。
2. 两条手臂分支一起前移，为胸腹和喙留出空间，武器挂点一起跟随。
3. 基于原版生成 44 个独立命名的 `.anim` 副本，适配局部平移，减小连续颈部和躯干的过度扭转。
4. 保留原动作帧数、原始小数帧率和缩放/武器显隐轨道，沿用原版状态转换和特效触发时刻。
5. 用解析矩阵平移保留原版极小缩放的武器挂点数据，避免导入工具的归一化导致挂点失真。

所有适配只写入 `APDC_penguin` 目录，不修改原版动画，不改变其他国家步兵。企鹅没有人类手指，鳍状手臂以贴近和夹持武器的方式表现。

## 文件与规格

- `gfx/entities/APDC_penguin_infantry.gfx`：三个模型/动画映射。
- `gfx/entities/zz_APDC_penguin_infantry.asset`：仅 `MAD` 的 9 个实体。
- `gfx/models/units/APDC_penguin/APDC_penguin.mesh`：11,104 个三角面、6,312 个导出顶点、33 个骨骼，每顶点最多 4 个权重。
- 同目录 3 张 1024×1024 DDS，DXT5/BC3、11 级 mipmap，使用原版 `PdxMeshAdvanced`。
- `gfx/models/units/APDC_penguin/animations/`：适配动作及注册文件。
- `art_source/penguin_infantry/APDC_penguin.blend`：可编辑源模型、蒙皮、适配骨架和待机动作，已打包材质。
- 同目录保留 PNG 贴图源和 `validation.json` 验证记录。

地图实体缩放为 `0.77`，站立高度按原版步兵接近的尺度制作，而非按真实企鹅与人的身高比例缩小。

## 重建顺序

1. Blender 4.2 后台运行 `build_penguin.py -- --project 项目 --exporter io_pdx_mesh目录 --delivery 交付目录`。
2. 普通 Python + Pillow 运行 `finish_penguin.py 交付目录`，生成带 mipmap 的 DDS。
3. Blender 后台运行 `verify_penguin.py`（同第 1 步参数），重新读取最终 `.mesh` 和 DDS，检查全部动作并输出姿态预览。`--quick` 仅用于建模迭代，不代替完整检查。
4. 普通 Python 运行 `validate_install.py io_pdx_mesh目录`，检查配置、资源引用、骨骼权重及动画副本。

导出工具及 Blender 仅作本机工具使用，不捆绑第三方工具源码进游戏目录。

## 验证边界

文件回读和后台动作检查不等同于钢四进程内实测。此次没有启动或操控游戏；需要重启游戏后查看马达加斯加普通步兵的默认外观，观察待机、移动及战斗。已有存档可用于模型检查；若编制手动选择了别的模型，应切回默认步兵外观。

最终桌面预览均由游戏用 `.mesh` 和最终 DDS 重新导入后渲染，不是单独绘制的效果图。实际游戏光照和地图距离下的材质表现可能不同。
