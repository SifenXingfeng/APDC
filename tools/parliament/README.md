# 议会系统维护入口

2026-11-07后续UI修正：法案选项行与侧栏直接读取经济系统GUI；不要再手工另写近似布局。窗口使用原生背景、被动文字使用 alwaystransparent，列表与对应按钮共用父GUI上下文。入口按政治页原图y=44对位，讲台点击框取当前素材实际尺寸。证据见[九项修正记录](../../docs/parliament/20261107-ui-corrections/README.md)。

议会基础算法、通用法案和静态UI保留开发生成器；候选人及特殊法案由作者直接维护原生运行脚本，新增不执行Python，见[原生内容接口](../native_content.md)。设计约定见[议会设计](../../项目接手文档/03_待实现设计/议会系统_已确认设计与实施计划.md)，本轮交付证据见 [20261107 实装记录](../../docs/parliament/20261107-implementation/README.md)。

## 配置与重建

| 来源 | 用途 |
|---|---|
| `data/laws.json` | 六组43档通用法案，保留用户文档原文效果 |
| `data/regimes.json` | 九种政体、议会名称、审议基础天数、加成比例与反对权 |
| `data/opening_countries.json` | 344个当前正式身份的临时开局配置，包括未来释放国家 |
| 原生候选脚本 | `common/scripted_effects/apdc_candidates_*.txt` 及新增独立文件，含登记、条件、头像与成员/首席回调 |
| `data/candidates.json` | 仅保留迁移来源快照，不再驱动候选名单、头像或任命逻辑 |
| `data/attitude_sources.json` | 可显示的额外态度来源；可以继续追加，不限制为三行 |
| 原生特殊法案脚本 | `common/scripted_effects/` 中各自独立的法案文件；新增内容不经过Python |
| `data/special_bills.json` | 旧JSON内容的兼容入口，默认空；不再作为新增特殊法案的推荐来源 |
| `data/settings.json` | 费用、可扩展选举周期、人力结算解释等初始平衡参数 |
| `data/seat_layout.json` | 生成的500席点位、行数与顺序，无须手工逐点修改 |

统一从 `python -X utf8 tools/compile.py parliament` 重建，会先在项目外建立新的备份。修复同一轮生成时可用 `--backup <该轮备份目录>`，原始字节只保存一次。然后运行 `python -X utf8 tools/compile.py parliament-check`。统一入口及发布边界见[tools/README.md](../README.md)。不要用旧历史、旧草案整体覆盖当前国家配置。

`--import-data` 仅用于有意重新导入项目内的原始法案Word，会重建导入配置，不是日常重建必选项。全部议会PNG、经济体制图标和原始Word已保存在 `tools/assets/parliament/`，重建不访问桌面。原版素材位置可用 `--game-dir <游戏安装目录>` 或 `APDC_GAME_DIR` 指定。`legacy/` 是旧内阁代码的生成参考，不是独立可加载模组。原有真实成员效果和六席内阁分配方式继续保留。

## 剧情接口

正式运行API采用原生“临时输入变量 + `effect = yes`”。生成器源码里的大写命名参数只是生成时简写，不能复制进HOI4脚本。

```text
# 在当前国家作用域，将先锋社与广泛社放入同一选举同盟。
set_temp_variable = { apdc_parl_arg_ID = 7 }
apdc_parl_set_communism_electoral_alliance = yes
set_temp_variable = { apdc_parl_arg_ID = 7 }
apdc_parl_set_socialism_electoral_alliance = yes

# 解除选举同盟；落败本身不会自动解除。
apdc_parl_clear_communism_electoral_alliance = yes

# 执政联盟继续使用原有API。仅剧情调用，没有玩家组建按钮。
APDC_add_social_democracy_to_governing_coalition = yes
APDC_remove_social_democracy_from_governing_coalition = yes

# 永久态度来源：同名set会更新已有来源，add可以追加。
set_temp_variable = { apdc_parl_arg_NAME = token:apdc_parl_source_story }
set_temp_variable = { apdc_parl_arg_VALUE = 15 }
apdc_parl_set_social_democracy_attitude_source = yes

# 当前法案态度，按百分点输入，不改变对政府态度或民意。
set_temp_variable = { apdc_parl_arg_VALUE = 20 }
apdc_parl_change_social_democracy_bill_attitude = yes

# 原生日历周期：月数24=两年，0=无选举。
set_temp_variable = { apdc_parl_arg_MONTHS = 24 }
apdc_parl_set_election_interval = yes
apdc_parl_force_election = yes

# 直接剧情立法绕过玩家提案；propose版本仍走费用和完整审议。
apdc_parl_enact_women_rights_3 = yes
apdc_parl_propose_women_rights_4 = yes
```

九种党派key按 `communism/socialism/social_democracy/liberalism/conservatism/authoritarianism/dictatorship/fascism/fundamentalism` 排列。来源token须登记在 `attitude_sources.json` 后重建；不能传未登记的名称并期待悬浮窗自行产生新行。额外周期可在 `settings.json` 的 `additional_election_intervals` 中添加原生月数再重建。

候选ID稳定，已有1—47保留，新增记录只能追加ID，不重新编号。`member_traits`、`chief_traits` 引用现有原生特质；`member_modifiers`、`chief_modifiers` 可填写显式修正。旧的 `member_idea` 优先保留真实顾问效果。未指定的首席特质当前为空，后续逐人制作。普通六槽使用成员效果，总理和副总理使用首席效果；更换和调岗会先撤销旧岗位效果。同一人物不能同时占两个岗位。

```text
# 选择岗位1—6，或7总理、8副总理，再任命候选ID。
set_temp_variable = { apdc_parl_arg_ROLE = 7 }
apdc_parl_select_role = yes
apdc_parl_appoint_1 = yes
```

任命入口仍执行阵营、名额与费用检查。每次成功选举分别授予总理、副总理各一次免费初任；更换已使用过的职位收费。胜选集团内部推举席位最多的合法党为执政党；同席先比原始民意，再抽签。不同集团第一名同席则保留现任、半年后重选，不用此内部推举规则打破胜负平票。

## 特殊议案与预留能力

**新增特殊法案直接写原生脚本，不需要运行编译器。** 按[原生法案制作说明](special_bills.md)复制模板，在独立文件中填写显示条件、可用条件、费用及提交/通过/失败效果；本地化按普通模组方式维护。引擎直接加载这些文件，议会核心通过原生 `meta_effect` 分发，不需要编辑中央名单或分发表。

剧情里用一行解锁，例如 `GER_example_special_bill_unlock = yes`。各国可继续追加不同法案；数字ID及法案key发布后保持稳定。通用界面、三阶段审议、投票和存档沿用现有系统。

旧JSON目录仍兼容，已有的直接注册API和作者回调也保留：

```text
set_temp_variable = { apdc_parl_arg_ID = 10001 }
set_temp_variable = { apdc_parl_arg_NAME = token:my_special_bill_name }
set_temp_variable = { apdc_parl_arg_DESC = token:my_special_bill_desc }
set_temp_variable = { apdc_parl_arg_COST = 100 }
apdc_parl_register_special_bill = yes

set_temp_variable = { apdc_parl_arg_ID = 10001 }
set_temp_variable = { apdc_parl_arg_AVAILABLE = 0 }
apdc_parl_set_special_bill_availability = yes
```

手动名称/说明需自行添加本地化及 `common/synchronized_dynamic_tokens`。原生法案的回调直接写在各法案文件中，不向本节旧全局hook追加ID分支。旧 `apdc_parl_special_submitted_hook`、`apdc_parl_special_passed_hook`、`apdc_parl_special_failed_hook` 位于作者维护的 `common/scripted_effects/apdc_parliament_story_hooks.txt`，继续供旧内容及通用剧情使用。回调中的ID仍为 `apdc_parl_bill_target`、`apdc_parl_last_passed_special_id` 或 `apdc_parl_last_failed_special_id`。运行中隐藏或撤回列表条目不会丢失已提交议案的名称和原生回调key。

经济入口和经济法案共用原有 `APDC_set_economic_system_<key>`；政治体制法案和顶部政体共用 `apdc_parl_regime`，不要维护第二套独立状态。

人形科技、遗迹专项计划仅预留 `apdc_parl_doll_research_factor`、`apdc_parl_relic_project_factor` 及 `apdc_parl_relic_research_forbidden`，待对应科研内容制作时读取。全局科研和专项计划速度已接原生修正。收购/掠夺预留 `APDC_eco_can_acquire_private`、`APDC_eco_can_plunder_private` 与收购价格系数，尚不执行企业交易。

## 存档与验证

`apdc_parl_initialized` 保证初始化只做一次。席位、抽签结果、同盟、态度来源、岗位ID、免费次数、在审议案和已完成工作量均使用国家持久变量/数组/标记；打开面板只刷新派生值，不重新分席。换届不清除法案和态度来源。法案结束才清除该项法案态度。

`runtime.py` 仅准备独立QA配置，不启动游戏；`watch_runtime.py` 读取测试日志、统一自有私有窗口尺寸并执行PrintWindow；不切换输入桌面，不发送鼠标键盘输入。验证应区分后台流程、存档数据、实际画面和真人鼠标/滚轮操作。不要声称后台改变量等于人工点击验收。
