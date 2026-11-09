# 项目同步与 GitHub 合并（2026-11-09）

本地原基准为 `b8b20a9f3b6881d23eae7a093211c4628d05d53b`。当前工作区的 3,935 项已有改动已保存为本地快照 `ff313df7f8621fcbd83dc3fa00785a0f357a4260`，涵盖地图、议会、国家人物、界面及维护资料；既有删除与改名保持。

GitHub `main` 更新至 `c6a69d607a1dd070908161c40c6f615d4b8678f4`，新增两个建设界面提交，仅涉及以下四张图片：

- `gfx/interface/buildings/APDC_building_icon_strip.dds`
- `gfx/interface/construction_screen_top.dds`
- `gfx/interface/convert_ic_button.dds`
- `gfx/interface/production_line_arrow_left.dds`

双方改动路径没有重叠，`git merge-tree --write-tree` 预检无冲突。实际合并提交为 `3c5c8c4cd4b7c190885216d4f019a9647a040a3e`，其树对象与预检完全一致。

逐项 Git 对象核对：本地快照共有 30,775 个文件；其中 30,773 个对象及模式保持不变，仅两张图片采用远端更新，另增加两张远端图片。四张图片均与远端对象完全一致，所有本地删除项没有被恢复。另行提交的本篇记录及接手资料 Git 状态更新属于本轮同步说明。

同步前已保存全部受版本管理及待新增文件的原始字节 SHA-256 清单、3,935 项变动的原文件、二进制补丁和完整 `.git` 备份。备份位置：

`D:/C-Drive-Migration-20260929/Permanent/Users/ASUS/Documents/Paradox Interactive/Hearts of Iron IV/mod/.codex_backups/APDC/20261109-222712-github-upload`

该目录保存 `before-manifest.json`、`preflight.json`、`merge-preflight-output.txt` 和 `merge-verification.json` 等原件。备份后、提交前的全量指纹核对未发现工作区漂移，未发现超过 100 MiB 的项目文件。

目标仓库为 `https://github.com/SifenXingfeng/APDC`，目标分支为 `main`，使用保留双方历史的普通推送，不使用强制推送。本轮仅进行项目保存、Git 合并与完整性核对，未启动游戏，不将合并检查描述为运行或视觉验收。
