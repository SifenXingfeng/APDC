# 地图维护基线

本目录保存移植后地图收尾需要的固定数据，不参与游戏直接加载。

- `original_economy`：原 GF 地图的 1133 州人口/资源/地块基准，仅用于按地块数比例重算经济数值。国家关系不能从中恢复。
- `original_economy_provenance.json`：来源文件指纹与版本凭据。
- `imported_definition.csv`、`imported_provinces.bmp`：导入时的地块身份与图形基准；修改地块 ID 或形状时先建立来源关系。
- `imported_apdc_states`、`current_state_files.json`：移植完成的 APDC 州历史与正式文件名，包含主项目身份及保留的州级元数据。
- `initial_territories.json`：最新权威 APDC 初始所有者、控制者、核心、宣称。
- `tag_mapping.json`：已确认的 GF 身份到 APDC 身份映射；SUD 是按州拆分，不是单一 tag 字符串替换。
- `modern_victory_points.json`：现代城市宿主、分数和十语名称；保留用户明确指定的麦地那落点。
- `imported_allocation*.json`：导入数值的分配凭据。内部 GF 绝对路径是来源记录，不是当前 APDC 文件路径；当前路径以 `current_state_files.json` 为准。

后续修改需同步当前基准；保留本轮固定原经济基准的原貌。完整执行规则见项目根 `AGENTS.md`。
