# 直接添加候选人、冷战行动和合作组织规则

这些内容现在由游戏直接加载原生脚本。新增时不编辑JSON、中央名单、GUI分支或Python，也不运行编译器。原生特殊法案仍按 [特殊法案说明](parliament/special_bills.md) 制作。

## 最短制作流程

1. 从 `tools/templates/` 复制所需的 `.txt.example` 到 `common/scripted_effects/`，去掉 `.example` 后缀，改成自己的文件名、永久数字ID和内容。
2. 把文本条目放入正常本地化文件，新增元数据token放入 `common/synchronized_dynamic_tokens/`。自定义头像照常添加图片及 `.gfx`；使用现成头像可直接引用其sprite。
3. 在事件、国策、决议或独立 `on_actions` 文件中调用本内容的命名包装。例如：

```text
GER = { GER_example_candidate_register = yes }
GER = { GER_example_action_unlock = yes }
SOV = { APDC_example_rule_register = yes }
```

登记后，候选列表、行动列表及组织列表/队列/投票显示由共享接口处理。游戏内条件变化可改变显示和可用性；剧情可在游戏运行时调用登记接口。新增磁盘文件按普通模组方式重新加载游戏，不需要外部重建。

`on_startup` 只用于新开局。希望新内容也能自动进入已有存档时，使用示例中的按国家每日登记钩子，或由事件/国策/决议显式调用；不依赖重跑编译器。原231条候选和40组规则另有一次性旧档接入，仅用于保留原内容，不是新增条目要修改的中央清单。

## 候选人

模板：[native_candidate.txt.example](templates/native_candidate.txt.example)。填写姓名、头像、人物token、九类党派之一及条件；成员与首席的实际效果分别放在任命/卸任回调中。`setup` 只填写元数据和条件，不能在那里增加奖励，因为它会重复执行。

新头像推荐使用与现有成品一致的156×210透明画布，再直接定义普通sprite，无须批量生成全部头像。

先调用内容自己的登记包装。剧情直接任命时，可调用模板中的任命包装，或设置 `apdc_nc_id`、`apdc_parl_selected_role` 后调用 `apdc_appoint_candidate = yes`。职位1至6为成员，7为总理，8为副总理。直接任命仍检查所属党派、赢家、配额、费用和是否可用。

共享代码按真实人物token去重，防止同一个人在不同候选记录下占据多个职位。`apdc_unregister_candidate` 只从候选池撤下该ID；已任职者的正常卸任接口仍为 `apdc_parl_clear_role_1` 至 `_8`。任职中的历史ID和回调不要删除。

当前231条原有记录已转到 `common/scripted_effects/apdc_candidates_<国家>.txt`；原头像与成员/首席ideas保留。新增人物可使用任意独立脚本文件名，不必加入这些旧文件。

500席是固定界面布局。每次选举的席位分配在游戏内计算，添加候选人不需要重新生成席位。

## 全部冷战行动

模板：[native_cold_war_action.txt.example](templates/native_cold_war_action.txt.example)。政治、经济、军事，对外施加影响、本国提高自主、接受其他国家影响，都使用同一套定义。目标和受益国决定影响关系，不需要单独制作一套GUI。

填写三轴之一、目标国、受益国、日变化、切换费用、名称/说明和条件。`rate = 0` 可用于只有自定义回调的行动。额外效果分别放在 `_on_execute`、`_on_stop`、`_on_daily`，不要重复实现共享代码已经处理的日变化。

解锁默认不执行；重复解锁保留原执行状态和已获得的份额。剧情直接执行/停止可用模板命名包装，或设置 `apdc_na_id` 与 `apdc_cw_target` 后调用 `apdc_execute_cold_war_action` / `apdc_stop_cold_war_action`。调用仍检查费用和可用性。`apdc_remove_cold_war_action` 停止并撤下记录，重复移除不会再次调用停止回调。

名字、说明及饼图贡献来源均从运行记录读取，不需要补按ID分支。切换维持原有同价规则；停止不撤销历史份额。可干涉、已控制和国际地位仍是各自独立的剧情接口。

原有28条测试行动在 `common/scripted_effects/APDC_cold_war_laws.txt`，原解锁名称保留；它们不是今后新增内容必须修改的中央目录。

## 合作组织规则

模板：[native_organization_rule.txt.example](templates/native_organization_rule.txt.example)。在组织锚点国家作用域调用登记包装，成员不直接持有权威规则状态。列表、队列、当前投票和成员视图自动使用定义中的名称与选项说明。

成员剧情直接提案可调用模板的命名包装，或设置 `apdc_nr_id`、`apdc_nr_option` 后调用 `apdc_propose_organization_rule = yes`，仍经过正常可用性、排队和投票流程。

`_on_enact` / `_on_repeal` 在锚点执行；`_on_member_apply` / `_on_member_remove` 在各成员执行；`_on_fail` 在提案未通过时执行。首次登记实施默认项一次；规则通过后先撤销旧项效果，再实施新项。成员加入应用当前项，退出移除其效果；组织解散同时撤销锚点和成员效果。

回调里的 `apdc_nr_old_option`、`apdc_nr_new_option` 表示旧/新选项；成员回调还提供 `apdc_nr_anchor` 和 `apdc_nr_rule_id`。内容作者负责在移除回调中对称清理自己添加的持续效果。一次性奖励不要放在会对新成员执行的持续效果回调里。

重复登记只刷新元数据，保留已通过的选项、投票锁及在途队列。纯条件每天刷新；显式可用性API的覆盖仍有效。当前界面为5个分类、每组最多4个选项，这与可以追加多少规则组无关。

现有40组占位内容已转到 `common/scripted_effects/apdc_organization_rules_baseline.txt`。原本未设计的正式规则效果仍留空，没有擅自补奖励。新规则直接填写自己的真实回调即可，不需要改投票算法。

## 文本、ID和验证

[文本示例](templates/native_content_l_simp_chinese.yml.example)、[token示例](templates/native_content_tokens.txt.example)、[独立开局登记示例](templates/native_content_on_actions.txt.example) 可配套复制。脚本UTF-8无BOM，本地化UTF-8 BOM。

永久数字ID用于保存身份，token只作当前显示。新增文件使token内部编号变化时，框架重新从定义绑定显示数据与人物，不以旧token数值分派回调。不要重排、复用正在存档中使用的ID；旧存档仍会调用到的定义和清理回调应保留。

可选只读检查：

```text
python -X utf8 tools/compile.py native-content-check
```

检查不生成内容。游戏玩家无需Python；发布可排除整个 `tools/`，保留 `common/`、`interface/`、`gfx/`、`localisation/` 等实际运行文件。旧 `candidates.json`、冷战 `laws.json` 只保留迁移来源，不再是这三类内容的制作入口。
