# 原生特殊法案制作

新增或修改法案不运行Python。游戏直接加载普通 `.txt` 和本地化文件，议会的通用界面与审议流程自动处理；只有修改议会通用规则时才需要维护系统生成器。新增文件后重新进入游戏读取内容，和添加普通决议一样。

## 新建一条法案

1. 将 [special_bill.txt.example](templates/special_bill.txt.example) 复制到 `common/scripted_effects/APDC_special_bills_GER.txt`。也可以在同一国家文件里继续添加其他法案。把 `GER_example_special_bill` 在该文件中统一替换为正式key，把示例 `10001` 统一替换为唯一数字ID，包括 `apdc_parl_bill_10001_key` 身份桥的名称。
2. 按模板填写 `_setup` 内的可见条件、可用条件和 `apdc_parl_arg_COST`。可见时调用 `apdc_parl_show_special_bill = yes`；可用时调用 `apdc_parl_allow_special_bill = yes`。条件不成立时保持默认隐藏或不可用。费用最低为0。
3. 在同一文件的 `_on_submit`、`_on_pass`、`_on_fail` 中填写原生效果。没有效果的回调保留空块，不删除名称。
4. 将 [本地化模板](templates/special_bill_l_simp_chinese.yml.example) 的两个键加入正常本地化文件，并将 [同步键模板](templates/special_bill_tokens.txt.example) 的相同两个键加入 `common/synchronized_dynamic_tokens/APDC_special_bills_GER.txt`。同一国家的法案可以共用这两个内容文件。
5. 在国策、事件或决议效果中调用 `GER_example_special_bill_unlock = yes`。若希望开局即解锁，使用可选的 [on_action模板](templates/special_bill_on_actions.txt.example)。不修改议会核心、JSON目录或分发表。

名称使用法案key本身，说明使用 `<key>_desc`，与原版决议的命名习惯一致。无需为法案另建GUI、事件命名空间或Python生成程序。模板放在 `tools/` 中，不会自动变成正式游戏内容。

## 刷新与生命周期

- 解锁会立即更新目录；重复解锁相同ID不会重复添加。
- `_setup` 在目录刷新时重新计算显隐、可用性和费用。这里只写条件与元数据，不放发钱、加稳定度或其他奖励。
- `_on_submit` 在成功支付费用并进入议程时执行；`_on_pass`、`_on_fail` 在对应结果产生时立即执行。正常刷新不执行这些效果。
- 通用三阶段审议、民意/席位计算、加速、谈判和同一时间一个议程的规则保持。
- 已提交法案捕获自己的名称和回调key。审议期间隐藏或撤回列表项后，原议案仍按原key结算。
- 数字ID和在审议案写入存档，运行时通过 `apdc_parl_bill_<ID>_key` 身份桥重新取得当前key。这样新增文本键改变引擎内部编号后，也不会串到别的法案。发布后不复用ID，不擅自改key；旧存档尚可能引用的身份桥和回调定义必须保留。

彻底撤回某条法案可以在国家作用域写：

```text
set_temp_variable = { apdc_parl_arg_ID = 10001 }
apdc_parl_lock_special_bill = yes
```

## 可选检查

```text
python -X utf8 tools/compile.py parliament-bills-check
```

这个命令只检查重复ID、回调、同步键和本地化，不生成或修改文件，亦非新增法案的必经步骤。旧 `special_bills.json` 及直接注册接口继续兼容；同一个ID不能同时用于原生文件和旧JSON。

引擎依据为当前安装版本的 `documentation/effects_documentation.md` 中 `meta_effect` 及原版 `CZE_scripted_effects.txt` 的动态分发写法。实现使用真实的原生脚本字段，不新增引擎不认识的 `common/special_bills` 数据库或仿原版字段。
