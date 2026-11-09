# 议会系统维护入口

2026-11-07后续UI修正：法案选项行与侧栏直接读取经济系统GUI；不要再手工另写近似布局。窗口使用原生背景、被动文字使用 alwaystransparent，列表与对应按钮共用父GUI上下文。入口按政治页原图y=44对位，讲台点击框取当前素材实际尺寸。证据见[九项修正记录](../../docs/parliament/20261107-ui-corrections/README.md)。

运行脚本由本目录的 Python 生成器和 `data/` 中的正式配置生成。设计约定见[议会设计](../../项目接手文档/03_待实现设计/议会系统_已确认设计与实施计划.md)，本轮交付证据见 [20261107 实装记录](../../docs/parliament/20261107-implementation/README.md)。

## 配置与重建

| 来源 | 用途 |
|---|---|
| `data/laws.json` | 六组43档通用法案，保留用户文档原文效果 |
| `data/regimes.json` | 九种政体、议会名称、审议基础天数、加成比例与反对权 |
| `data/opening_countries.json` | 344个当前正式身份的临时开局配置，包括未来释放国家 |
| `data/candidates.json` | 持久候选ID、所属党、角色与头像、成员/首席两套特质及显式修正 |
| `data/attitude_sources.json` | 可显示的额外态度来源；可以继续追加，不限制为三行 |
| `data/special_bills.json` | 默认空的逐国特殊议案目录，含可见/可用条件及提交、通过、失败效果 |
| `data/settings.json` | 费用、可扩展选举周期、人力结算解释等初始平衡参数 |
| `data/seat_layout.json` | 生成的500席点位、行数与顺序，无须手工逐点修改 |

运行 `python -X utf8 tools/parliament/build.py` 会先在项目外建立新的备份。修复同一轮生成时可用 `--backup <该轮备份目录>`，原始字节只保存一次。然后运行 `python -X utf8 tools/parliament/verify.py`。不要用旧历史、旧草案整体覆盖当前国家配置。

`--import-data` 仅用于有意重新导入桌面原文，会重建导入配置，不是日常重建必选项。美术导入使用用户提供的桌面PNG及Word中九张政体图标；重建这些素材时需要原来源文件仍在。`legacy/` 是旧内阁代码的生成参考，不是独立可加载模组。原有真实成员效果和六席内阁分配方式继续保留。

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

优先在 `special_bills.json` 追加条目并重建，生成器负责本地化、token、条件和三种生命周期回调。也支持手动运行注册：

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

手动名称/说明需自行添加本地化及 `common/synchronized_dynamic_tokens`。`apdc_parl_special_submitted_hook`、`apdc_parl_special_passed_hook`、`apdc_parl_special_failed_hook` 位于作者维护的 `common/scripted_effects/apdc_parliament_story_hooks.txt`，生成器不会覆盖其中已写的剧情。回调中读取 `apdc_parl_bill_target`；通过/失败记录分别保存在 `apdc_parl_last_passed_special_id` 和 `apdc_parl_last_failed_special_id`。运行中移除列表条目不会丢失已在审议议案的名称。

经济入口和经济法案共用原有 `APDC_set_economic_system_<key>`；政治体制法案和顶部政体共用 `apdc_parl_regime`，不要维护第二套独立状态。

人形科技、遗迹专项计划仅预留 `apdc_parl_doll_research_factor`、`apdc_parl_relic_project_factor` 及 `apdc_parl_relic_research_forbidden`，待对应科研内容制作时读取。全局科研和专项计划速度已接原生修正。收购/掠夺预留 `APDC_eco_can_acquire_private`、`APDC_eco_can_plunder_private` 与收购价格系数，尚不执行企业交易。

## 存档与验证

`apdc_parl_initialized` 保证初始化只做一次。席位、抽签结果、同盟、态度来源、岗位ID、免费次数、在审议案和已完成工作量均使用国家持久变量/数组/标记；打开面板只刷新派生值，不重新分席。换届不清除法案和态度来源。法案结束才清除该项法案态度。

`runtime.py` 仅准备独立QA配置，不启动游戏；`watch_runtime.py` 读取测试日志、统一自有私有窗口尺寸并执行PrintWindow；不切换输入桌面，不发送鼠标键盘输入。验证应区分后台流程、存档数据、实际画面和真人鼠标/滚轮操作。不要声称后台改变量等于人工点击验收。
