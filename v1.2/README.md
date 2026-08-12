# lwMAA v1.2 桌面壳维护说明

`v1.2/` 是对 `v1.0/` 的轻量化重构实验版：界面层改为 `HTML + CSS + JavaScript`，Python 负责本地 HTTP 后端和伤害计算，桌面入口使用 `pywebview` 打开内嵌 WebView 窗口。目标是保留“一个软件窗口”的体验，同时去掉 PySide6 依赖，降低打包体积，并让 UI 维护更直观。

## 最近更新

- 修正弹幕灵力回收公式：普通伤害计算和复灵模拟都按 `power_rate * 4 * 5 / 10000 * 实际命中次数` 计算期望，其中 `rand(3,7)` 取平均值 5；ID17 绘卷/技能回收倍率和复灵 tag 回收倍率仍作为乘区叠加。
- 复灵模拟的手动技能改为写入回合运行态，不再直接污染“我方参数”预设页；当前 P 最高限制为 5.0，重新初始化会回到开战快照，后端计算前也会用 `manual_state` 兜底合并当前 P、buff、异常盾和剩余 HP。
- 角色详情从 ID 载入时，左侧侧边栏会继续显示“角色查询 / 绘卷查询 / 角色详情”三个查询模块导航，不再变成空导航。
- 新增 `backend/parsers/arena_txt_parser.py`，用于解析 `擂台敌人数据07-12.txt`；只补全完全没有擂台预设的角色，保留已有预设不覆盖，2 开头写入周擂台1，3 开头写入周擂台2，气质默认全普通、敌方技能为空。
- 前端继续拆分：新增 `web/core.js` 承载基础常量、API、格式化和资源 URL 工具；新增 `web/components/vs_display.js` 和 `web/components/role_gallery.js`，分别承载复灵展示 helper 和角色总览渲染逻辑，避免继续把所有 UI 细节塞进 `app.js`。
- 前端继续模块化：`web/app.js` 只保留全局状态、少量预设依赖桥接、事件绑定和初始化；伤害参数槽、伤害运行时、周擂台、复灵模拟、查询详情、筛选控件、角色/擂台预设等页面逻辑已拆到 `web/modules/`。
- 顶部主导航保持不变；左侧侧边栏改为当前模块内快速导航，默认折叠，仅用于伤害计算、复灵模拟、查询等模块的子页面跳转。
- 左侧侧边栏的折叠行为改为向左收缩，展开宽度缩小为原先的一半，并保持 sticky，滚动时和顶部导航一样留在可视区域内。
- 复灵模拟回合操作新增固定“应用技能”按钮：技能按钮只负责标记待释放，点击应用后才写入当前棋盘 buff/P 点/异常盾并进入 CD。
- 复灵模拟区分开战前参数和回合模拟运行状态；重新点击“初始化回合模拟”会恢复开战快照，避免上一轮计算后的 HP/P/盾/buff 污染新模拟。
- 复灵模拟状态同步补强：计算后会回写敌我运行 buffs、当前 P、当前护盾、异常盾、FB 状态和 `当前HP/血量上限`，下一回合重新收集 payload 时不会丢失状态。
- 普通伤害计算结果新增灵力变化摘要；角色详情的攻击类型部分新增 0P-3P 灵力回复期望，群体攻击以 `×n` 标注目标人数变量。
- 复灵模拟敌方技能改为敌方行动效果：敌方未 FB 时按敌方视角 target 映射后施加到我方，敌方 FB 时跳过；回合结果不再把敌方技能混入敌方自身 buff 展示。
- 复灵模拟弹幕灵力回收已接入：按每个目标实际命中次数、攻击 `power_rate`、ID17 灵力回收 buff 和复灵 tag 灵力回收倍率计算，并写回我方当前 P。
- 复灵模拟气质展示只保留日/月/火/水/木/金/土/星八种属性，不再显示无属性。
- 后端大型服务已迁移：`DamageCalculatorService` 和 `CharacterIndex` 的实际实现移动到 `backend/services/calculator_service.py`；`gui/services.py` 只保留兼容 wrapper。
- 后端核心战斗文件已迁移到 `backend/core/`：`character.py`、`battle_op_state.py`、`buff_effect.py`、`damage_pipeline_skeleton.py`、`attack_order.py`、`combat_constants.py`。根目录同名 wrapper 已删除，代码应统一使用 `backend.core.*` 导入。
- 角色预设和擂台预设的角色预览区已移动到预设卡片上方，默认折叠；预览区带简单筛选和头像网格，点击头像会载入下方对应预设编辑卡片。
- 复灵模拟敌方参数和模拟对战敌方卡片中，气质改为单独一行展示；复灵相关头像大小提升 25%。
- 修复复灵 tag 全部显示“未知效果”：`/api/vs-presets` 重新返回 `vs_effect_rows`，前端翻译表同时建立 `kind/sub_id/value` 精确索引和 `kind/sub_id` 回退索引。
- 复灵预设和复灵模拟的 tag/effect 展示统一使用 `description`，翻译表未命中时显示“未知效果”，不再直接暴露 `kind/subID/value` 数字串。
- 复灵模拟敌方参数预览中，气质改为属性图片展示；Tribe 单独占一行并显示 `ID:名称`，方便核对种族特攻。
- 复灵模拟回合结果中的 buff 展示按 raw buff ID/subID 升序排列；敌方技能效果也会带 raw effect 返回给前端用于排序。
- 复灵回合模拟导入后会立即显示初始敌我状态总览，不再等第一次“计算本回合”；最终血条被打空的敌人会从后续模拟状态和总览中移除。
- 角色详情能力说明补充结界异常状态码：`1` 为免疫，`4` 为免疫且体力回复 5%，`6` 为阳攻/阴攻/CRI攻击/CRI命中上升，`7` 为阳防/阴防/CRI防御/CRI回避上升。
- v1.2 根目录文件继续分类：CSV 数据表移动到 `data_tables/`，复灵/擂台/原始角色解析器移动到 `backend/parsers/`；根目录解析器 wrapper 已删除，旧命令需改为 `python -m backend.parsers.xxx`。
- 角色预设/擂台预设的角色总览移除了额外强约束，恢复为原始小卡片网格排列。
- 复灵模拟的敌方参数预览支持按敌方位置切换血条，预览当前血条的 HP、六维、护盾、气质、tribe、敌方技能、EX 阶段效果、符卡效果和额外说明。
- 复灵模拟回合结果中，点击我方/敌方头像查看 buffs 时改为每条 buff 单独一行；摘要区域也按逐行展示，不再用斜杠拼成一行。
- 复灵模拟过回合切换到下一血条时，会同步恢复新血条的护盾数量并清空异常盾状态，返回状态中也写回 `barrier_count/barrier_types`。
- 新增 `web/components/manual_buffs.js`，把复灵手动模拟的 buff 逐行展示逻辑从 `app.js` 拆出；`web/components/vs_effects.js` 继续负责复灵 effect 翻译回填。
- 新增 `backend/services/buff_text.py` 和 `buff_effect_templates.csv`，技能/buff 文本会优先按 CSV 模板映射，未覆盖的 ID 继续走 `gui/services.py` 原代码兜底，方便后续单独维护中文说明。
- 周擂台求解详细模式合并了“角色筛选”和“角色下拉”：现在一个角色输入框同时支持输入中文筛选和下拉选择，选中项显示为“角色名/世界群”。
- `vs_effect_translation.csv` 改为只输出 `kind,sub_id,value,name,description`，并按 `kind/sub_id/value` 合并；`presets/vs/vs_enemy_data_06-19.json` 中 tag effect 也压缩为 `{kind, sub_id, value}`，前端按翻译表回填文本。
- 伤害计算与复灵模拟继续分离：伤害计算页不再可见选择复灵模式；复灵预设载入后进入复灵模拟模块，不再跳转到伤害计算的敌方参数页。
- 伤害计算模块的我方参数恢复可编辑初始 P 点、初始护盾数、目标敌人、开 P 数、开盾数量、攻击类型和 buffs；复灵模拟的我方参数保持只做初始化和绘卷配置，目标敌人/开 P/开盾/攻击类型在回合模拟阶段设置。
- 复灵模拟新增“敌方参数”子页，位于场地 buff 后，用于按复灵层数和 tag 预览敌方 HP、六维、护盾、气质和 tribe，方便 debug。
- 前端新增 `web/components/vs_effects.js`，先把复灵 effect 的 key、side 推断和翻译回填逻辑拆出 `app.js`；后端新增 `backend/README.md` 记录后续 API/解析器/服务层拆分方向。
- 新增 `backend/parsers/unit_raw_parser.py`，用于把 `unit260709/` 中的原始角色 key/value 数据批量导入 `datajson/`；重复 ID 会覆盖旧 JSON。当前已导入 58 个角色，并保留 12050 三技能大结界 60% 的已知修正。
- 复灵预设解析器升级到 `parser_version=6`：tag 组会优先按 `effect_group_id * 100 + 1..10` 匹配，避免 10057 等 `VS ID > 10001` 的预设被错误解析为 0 个 tag。
- 复灵模拟的场地 buff 阶段改为只勾选启用 tag，不再给每个 tag 设置层数；“复灵层数”只用于敌方 60-100 级六维插值，默认 100，并提供 tag 重置按钮。
- 复灵模拟的我方参数阶段改为每个角色单独一行，初始 P 点默认 1.0、初始护盾数默认 5、开盾数默认 0；该阶段隐藏 buffs，并把目标敌人、开 P 数、开盾数、攻击类型留到回合模拟阶段处理。
- 角色载入按钮逻辑已分离：`载入ID` 只按 ID 框载入；普通 `载入` 只按世界群/角色下拉载入，避免三个框都有值时被 ID 框误导。
- 周擂台求解详细模式中，敌方角色下拉项显示为“角色名/世界群”，并继续支持 ID 输入、世界群筛选、汉字名称筛选三种路径。
- 复灵预设的 tag/effect 展示默认折叠；伤害计算页的复灵 tag 分组也默认折叠，避免直接展开大量 effect。
- 复灵模拟拆成独立流程：场地 buff/tag 表格、复灵专用我方参数、回合模拟。复灵专用我方参数使用 `.vs-ally-slot`，不复用普通伤害计算页的 `.ally-slot` 数据。
- 复灵模拟中手动技能、开盾、开 P、攻击类型会从 `.vs-ally-slot` 生成 payload；技能释放顺序会显示在回合模拟结果中。
- 角色预设和擂台预设的角色总览卡片进一步压缩尺寸，避免一行只显示一个角色。
- L0o 古明地觉（ID 12050）的三技能第一条大结界效果已修正为 `1205001`：己方全体 CRI 防御上升 60%，敌方全体 CRI 防御下降 60%（3 回合）。破界效果仍按当前需求暂不实装。

## 当前结构

- `desktop_app.py`：正式桌面软件入口，启动本地后端并创建内嵌 WebView 窗口。
- `server.py`：本地 HTTP 服务和 API 定义，使用 Python 标准库 `http.server`，可单独作为调试入口。
- `web/index.html`：Web 前端页面结构。
- `web/styles.css`：Web 前端样式。
- `web/core.js`：前端基础工具、常量、API 调用、URL 和格式化 helper。
- `web/app.js`：前端入口和基础框架层，仅保留全局状态、事件绑定、初始化和少量跨模块桥接。
- `web/components/`：前端复用组件目录；当前已有 `vs_effects.js`、`vs_display.js`、`manual_buffs.js`、`role_gallery.js`。
- `web/modules/`：前端页面级模块目录；当前包含 `shared_forms.js`、`damage_slots.js`、`damage_runtime.js`、`weekly_arena.js`、`vs_manual.js`、`vs_manual_actions.js`、`query_detail.js`、`filters.js`、`character_query.js`、`equipment_query.js`、`presets.js`。
- `backend/README.md`：后端拆分规划说明；当前仍以 `server.py` 为 HTTP 入口。
- `backend/core/`：核心战斗计算模块目录；根目录同名 wrapper 已删除，新增代码应直接导入 `backend.core.*`。
- `backend/parsers/`：复灵 lua、擂台表格和原始角色数据解析器目录；根目录 parser wrapper 已删除，调试时使用 `python -m backend.parsers.xxx`。
- `backend/services/calculator_service.py`：原 `gui/services.py` 的大型服务实现，负责角色查询、绘卷查询、详情格式化、计算编排等。
- `backend/services/buff_text.py`：buff/技能说明模板加载与渲染工具，供 `gui/services.py` 调用。
- `gui/config.py`：沿用 v1.0 的配置 dataclass。
- `gui/resources.py`：v1.2 资源路径，已适配源码运行和 PyInstaller `_MEIPASS`。
- `gui/services.py`：兼容 wrapper，重新导出 `backend.services.calculator_service` 中的服务类。
- `equipment_parser.py`、`recommend_equipment.py`：沿用绘卷解析和推荐逻辑。
- `unit260709/`：新增角色原始数据目录，文件按 `{角色ID}unit`、`{角色ID}skill`、`{角色ID}1/1c/2/2c/5`、`{角色ID}chain`、`{角色ID}cos` 命名。
- `assets/avatars/`：角色头像目录，命名约定为 `S{角色ID}01.png`；缺失时回退到 `S0.png`。
- `presets/`：预设目录，当前用于保存 `character_presets.json`；目录内有 `.keep`，用于保证空目录也能进入打包产物。
- `data_tables/`：CSV 数据表目录，包含 `characters.csv`、`recommended.csv`、`buff_translation.csv`、`buff_effect_templates.csv`、`tribe_extracted.csv`、`vs_effect_translation.csv` 等。
- `datajson/`、`equipment_data.json`、`local_translations.json`：运行所需数据。

## 运行方式

在 `v1.2` 目录下运行：

```powershell
python server.py
```

这是调试后端入口。正式桌面窗口运行：

```powershell
python desktop_app.py
```

内嵌窗口内部地址由程序自动分配端口，通常不需要手动访问。调试后端默认地址为：

```text
http://127.0.0.1:8765/
```

如果只想启动后端，不打开窗口：

```powershell
python server.py --no-browser
```

或：

```powershell
python server.py --browser-mode none
```

如果想用普通浏览器标签页调试：

```powershell
python server.py --browser-mode tab
```

如果调试后端端口被占用：

```powershell
python server.py --port 8766
```

`desktop_app.py` 默认使用 `--port 0` 自动选择空闲端口，通常不会有端口冲突。

导入 `unit260709/` 新角色数据：

```powershell
python -m backend.parsers.unit_raw_parser --source .\unit260709 --output .\datajson
```

该命令会覆盖同 ID 的旧 JSON。导入后建议至少运行一次后端导入检查：

```powershell
python -B -c "import sys; sys.path.insert(0, '.'); import server, gui.services, backend.core.character, backend.parsers.vs_lua_parser, backend.parsers.unit_raw_parser; print('import ok')"
```

打包产物可用下面的内部测试参数只启动后端，不打开窗口：

```powershell
.\dist\lw_damage_calculator_v1_2\lw_damage_calculator_v1_2.exe --backend-only --port 8772
```

## 当前保留的功能

- 敌方 0-2 参数输入。
- 我方 0-2 参数输入。
- quality 三态切换和归零。
- 自定义 buffs。
- 五张绘卷输入和推荐绘卷填入。
- 自定义多角色技能顺序。
- 场地 buff：弹种、属性、type 伤害倍率。
- 单次计算。
- 伤害计算模块支持本地保存/载入计算预设，记录当前计算模式、三波敌方、我方参数、绘卷、buff、技能顺序和场地倍率；预设保存在浏览器/WebView 的 `localStorage` 中。
- 批量计算并导出 summary，输出到 `output/`。
- 角色查询。
- 绘卷查询。
- 角色详情展示。
- 总览模块，可点击敌我位置跳转到对应参数卡片。
- 总览模块已并入 `伤害计算` 子页面；周擂台模式可切换敌方 1-3 波，前端会保存三套敌方参数。
- 角色预设模块，当前单次编辑一个角色，支持六维加成、五张绘卷、未拥有标记、简略/详细绘卷展示，并保存到 `presets/character_presets.json`；上方折叠预览区可按预设状态、二转、未拥有筛选角色头像并载入。
- 擂台预设模块支持敌方六维、盾数量 3/5、气质贴图，并保存到 `presets/arena_presets.json`；上方折叠预览区可按是否已有擂台预设筛选角色头像并载入。
- 复灵预设模块会初步解析上级目录的 `复灵敌人数据06-19.lua`，输出到 `presets/vs/vs_enemy_data_06-19.json`。
- 复灵模拟模块支持载入当前复灵/敌我参数后按“应用技能 / 计算本回合 / 过回合”推进：计算不会自动增加回合，过回合会继承敌方剩余 HP；仅在当前血条清空且存在下一血条时切换血条，否则禁用该敌方。
- 复灵模拟中的我方技能需要先点击技能按钮标记，再点击“应用技能”才会生效；导入模拟时会清空原我方参数页的技能顺序，避免每回合自动释放三个技能。可解析的技能效果会写入当前敌我 buff/P 点/异常盾状态。
- 复灵模拟载入复灵预设时，会把已勾选 tag 中的敌方最大体力倍率直接折算进敌方 HP；发送计算 payload 时不再重复发送该 HP tag，避免最大体力上升被计算两次。
- 复灵模拟的手动技能已支持基础即时状态变更：`1/2/41/42` 层级 buff 写入并合并到 buffs 栏位，复合 subID 会拆分；`4` 增加结界但不超过当前血条上限；`5` 直接增加灵力；`6` 会把异常结界写入敌方 `barrier_types` 并传入后端计算。
- 复灵模拟的手动技能目标口径已和核心逻辑对齐：`target=0` 视为我方全体，而不是自身。
- 导入复灵回合模拟时会清空敌我双方旧 buffs 和手动异常盾状态，避免从普通伤害计算页面继承残留状态。
- 复灵模拟敌方卡片会显示剩余血条数和符卡 CD；过回合会递减 CD，归零时写入日志并保留后续插队释放接口。
- 复灵模拟计算结果会回写敌方剩余 HP 和结界状态；后端返回攻击前最大 HP 与攻击后剩余 HP，避免把核心扣血后的 `stats.hp` 误当成最大 HP。
- 复灵模拟计算结果会回写 FB 状态、当前 P、运行中 buffs，并在敌方 FB 时跳过敌方技能发动；敌方技能作为敌方行动施加到我方，不作为敌方自身 buff 展示。
- 周擂台求解支持“只考虑对应擂台加成 Type”开关，默认开启；每波答案候选只返回溢出大于 `-1000` 的角色，避免 0 伤害角色占据结果。
- 周擂台求解现在按每个敌人分别判断是否击破，不再只比较总伤害；多敌人波次会过滤终符为单体的角色，避免单体终符角色误入两个或三个敌人的答案。
- 周擂台求解会把当前擂台勾选的 Type 真正传入伤害流程，触发对应阴/阳擂台的攻击/防御翻倍；前端求解不再强制开启拟真随机，避免因 miss/暴击随机导致求解结果不稳定。
- 周擂台求解候选按逐敌人最小溢出判断，当前统一显示溢出大于 `-1000` 的角色；不再额外强制稳定通过。
- 周擂台求解的敌方 ID 输入框恢复为仅按数字 ID 选定角色，避免不同世界群存在同名角色时被名称解析到错误 ID。
- 周擂台求解的敌方选择支持两种路径：先选世界群再选角色，或先选角色再切换世界群并按角色名重定位同名角色；详细模式下选中后仍保留筛选控件，简略模式下只展示头像和摘要。
- 周擂台求解详细模式下敌方角色栏位支持按角色名输入筛选；角色下拉只显示角色名，选中后隐藏 ID/世界群/角色名/角色选择框，并在原位置显示重选按钮与盾/弱点/耐性摘要；简略模式只保留盾、弱点、耐性三行。
- 周擂台求解的 1039 擂台数据已按当前校验修正为火弱点而非火耐性；1110 为速攻角色，在速攻 Type 加成擂台中应触发对应翻倍。
- 周擂台敌方技能会按技能文本兜底修正弹种/属性减伤，避免表格解析出的旧 subID 错位；当前已同步修正 6049 体术弹减伤、1101 御符弹减伤和 1029 土属性减伤。
- 复灵模拟的“从当前伤害计算导入”会等待当前复灵预设应用完成；如果已有复灵预设但敌方槽位尚未载入或与预设敌方不一致，会先载入预设再收集手动模拟 payload。
- 复灵模拟页面拆为“场地 buff / 敌方参数 / 我方参数 / 回合模拟”四个子模块：先应用复灵 tag 和场地效果，再预览敌方状态、初始化我方参数，最后在回合模拟中计算本回合或过回合。
- 绘卷查询的 buff 筛选中，subID 会根据所选 buff ID 动态加载可选项，target 改为基于翻译表的下拉框。
- 擂台预设模块的载入入口统一为“载入预设”，载入后显示角色 ID、世界群、名称，并以五维覆盖展示周擂台数据。
- 角色查询/绘卷查询使用逐行筛选条件，可通过 tag 添加多选条件，结果支持折叠头像/图像栏。
- 顶部“角色/绘卷查询”入口默认进入角色查询页，避免进入空白分类页后还需要再点一次子模块。
- 拟真计算开关已接入：开启后后端会对命中和暴击做随机判定，并重新汇总本次返回伤害。

## 当前差异

这是 v1.2 的第一版桌面壳迁移，不是完全重写计算逻辑：

- 计算核心仍复用 v1.0。
- 查询和详情格式化仍复用 `DamageCalculatorService`。
- 前端没有使用构建工具，没有 npm 依赖，便于直接打包。
- UI 由系统 WebView 渲染，但默认是内嵌在应用窗口中，不启动外部浏览器。
- UI 布局和 PySide6 版不是像素级一致。
- 角色详情目前主要展示，不做复杂可视化编辑；后续可基于 `/api/characters/{id}/save` 扩展。

## API 概览

- `GET /api/bootstrap`：读取前端初始化数据，例如 type、属性、弹种、buff、绘卷选项。
- `POST /api/calculate`：单次计算。
- `POST /api/batch-summary`：批量计算并导出 CSV。
- `GET /api/characters`：角色查询。
- `GET /api/characters/{id}`：角色详情。
- `POST /api/characters/{id}/save`：保存角色 JSON，当前前端暂未开放编辑按钮。
- `GET /api/equipment`：绘卷查询。
- `GET /api/equipment/{id}`：绘卷详情。
- `GET /api/recommended?character_id=12087`：推荐绘卷 ID。
- `GET /api/character-presets`：读取角色预设。
- `POST /api/character-presets`：保存角色预设到 `presets/character_presets.json`。
- `GET /api/arena-presets` / `POST /api/arena-presets`：读取/保存擂台预设。
- `GET /api/vs-presets`：解析并读取复灵 raw data 预设。
- `GET /api/equipment-resolve?q=511`：按 ID 或名称返回绘卷摘要，用于前端绘卷栏展示。

## 打包

v1.2 推荐使用单独环境打包：

```powershell
cd C:\Users\Deity4113\Desktop\lwMAA\v1.1_test\v1.2
python -m venv .buildvenv
.\.buildvenv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean lw_damage_calculator_v1_2.spec
```

输出位置：

```text
dist/lw_damage_calculator_v1_2/lw_damage_calculator_v1_2.exe
```

注意：

- 当前仍是 `onedir`，不要只复制 exe。
- 由于去掉 PySide6，理论体积应明显小于 v1.1 PySide6 版。
- 当前 spec 使用 `console=False`，启动后表现为普通软件，不额外弹出控制台。
- 正式入口是 `desktop_app.py`，打包后是一个内嵌 WebView 的桌面窗口。
- `presets/` 会被打进 `_internal/presets`，程序启动时也会在 exe 同级创建可写的 `presets/`，用于保存用户预设。
- Windows 上需要系统具备 Microsoft Edge WebView2 Runtime。多数 Windows 10/11 已自带；如果目标机器缺失，需要安装 WebView2 Runtime。
- 关闭桌面窗口后，后端服务会自动关闭。
- 当前 spec 排除了 `PySide6`、`numpy`、`openpyxl`、`pandas`、`PIL`、`pygame`、`scipy`、`lxml`、`matplotlib`。
- 当前实测 `dist/lw_damage_calculator_v1_2` 约 47 MB。比纯外部浏览器壳的 32 MB 稍大，但换来了真正内嵌软件窗口。

## 后续优化方向

优先级较高：

- 将 `DamageCalculatorService` 拆成角色服务、绘卷服务、计算服务、翻译服务。
- 给 `/api/calculate`、`/api/equipment`、`/api/characters` 添加最小自动化 smoke test。
- 前端补角色详情编辑与保存。
- 前端 buff 输入改成可搜索下拉，同时复用后端 subID API。
- 批量 summary 增加浏览器下载入口，而不是只显示本地路径。
- 继续完善复灵模拟状态机：当前已支持手动技能写入、tag 乘区、异常盾传入计算、剩余 HP 继承和基础血条切换；后续还需要补敌方符卡 CD 插队、敌方技能触发条件、EX 清除 buff 规则、上锁效果和完整技能 CD 回合递减。
- 周擂台求解目前以“终符 + 三技能 + 推荐绘卷”的单角色模板遍历，后续如果要模拟多角色/多回合组合，需要单独扩展搜索器。
- 拟真计算目前按已算出的每 hit 期望值做随机重算，后续如果需要逐 hit 扣血完全拟真，需要下沉到 `damage_pipeline_skeleton.py` 的计算过程内部。

中期优化：

- 后续前端优化重点不再是继续缩小 `app.js`，而是把各页面模块内部再细分为更小组件，并逐步把适合常驻的筛选/预设/快捷操作迁入左侧侧边栏。
- 为绘卷查询的命中 buff 添加更明确的高亮。
- 给计算详情增加 trace 视图，解释每个乘区来源。
- 增加启动时资源完整性检查，提示缺失的 CSV/JSON。
- 将输出文件统一放到 `output/`，并避免污染源码根目录。

长期优化：

- 如果 v1.2 桌面壳稳定，可以逐步废弃 PySide6 版打包流程。
- 如果 `pywebview` 打包兼容性不稳定，可以退回 `server.py --browser-mode app` 的外部浏览器 app 窗口方案；如果体积允许，也可以重新评估 PySide6。
- 如果仍要进一步压缩体积，可尝试只保留 `.pyc` 或将数据资源压缩加载，但优先级低于功能稳定。
