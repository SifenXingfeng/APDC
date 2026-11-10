# 特殊法案改为原生文件扩展（2026-11-10）

新增特殊法案现在直接写普通游戏脚本和本地化，同步键按正常引擎格式登记，剧情中调用一行解锁。无需改JSON目录、中央分发表、GUI或重跑Python。制作入口和完整模板见 [special_bills.md](../../../tools/parliament/special_bills.md)。

每条法案自行提供身份桥、解锁包装、条件/费用及提交、通过、失败三个回调。核心通过原生 `meta_effect` 按稳定数字ID和key分发；原版同类用法来自安装版本的 `documentation/effects_documentation.md` 和 `common/scripted_effects/CZE_scripted_effects.txt`。未虚构新的引擎数据库或可自动读取的自定义字段。

旧JSON生成方式、手动注册API和全局剧情hook保持兼容；原生日历、500席、九党、六组法案、三阶段审议及任命规则保持。打开议会时刷新法案目录。正式模组没有擅自增加示例法案，所有例子均位于不被游戏加载的 `tools/parliament/templates/`。

## 存档身份

实际回归发现：在旧存档后增加同步文本键，会改变引擎内部token编号，直接保存并沿用原编号可能串法案。最终实现使用永久数字ID调用 `apdc_parl_bill_<ID>_key` 身份桥，恢复当前key，并刷新可见行和在审议案名称；通过/失败亦从对应稳定ID恢复回调。即使法案在审议期间隐藏或从目录撤回，结算仍找回原定义。

身份桥和回调发布后不得随意改名或删除。源码维护与生成器不会覆盖作者新增的法案文件。

## 验证

- [29项静态检查](static-verification.json)与[19项界面结构检查](static-ui-verification.json)通过。
- [首次实际开局](initial-verification.json)通过16项功能断言，并取得2060.2.1实际自动存档：10003号议案仍在审议，工作量60/120，两条原生目录记录及对应身份数据存在。
- [最终读档回归](reload-verification.json)通过24项断言：从上述真实存档恢复；在原三个文件之外增加第四个独立法案文件，并将其同步键文件放在原文件之前；原议案正确结算，新法案直接可用，其他回调不串、不重复；随后重放全部16项功能断言通过。
- 功能覆盖重复解锁、隐藏/不可用、动态价格、政治点不足、实际扣费、提交/通过/失败回调、回调解锁另一文件、目录刷新不重复奖励、旧注册API与hook、在审撤回及读档后的回调身份。
- 内容只读检查另覆盖合法独立文件、缺回调、重复ID、缺同步键、缺本地化、旧JSON冲突及身份桥错误，见 `content-check-verification.json`。

最终实际测试的法案相关引擎错误为零；实际启用DLC记录在报告内。使用APDC及专用QA覆盖层、GER 2060场景，未启用用户Toolpack。用户正常配置、继续游戏信息和自动存档不由此测试改写。没有把上述后台数据与接口验证描述为逐项真实鼠标点击或长期平衡验证。

过程中保留了失败证据：一次早期读档入口退出没有调用栈，不能由DLC校验提示认定崩溃根因；随后补齐测试继续游戏元数据后进入实际存档。另两轮回归分别暴露了token身份不稳定及开发中的阶段路由接错问题，均已修正并用同一存档复验通过。没有删除DLC或无关玩法来清理日志。

原字节、失败和最终日志、实际存档及私有进程清理记录保存在项目外备份：

`D:/C-Drive-Migration-20260929/Permanent/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/.codex_backups/APDC/20261110-120031-scripted-special-bills`

最终文件保护和进程状态见 [preservation-audit.json](preservation-audit.json)。
