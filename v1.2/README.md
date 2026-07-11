# lwMAA v1.2 桌面壳维护说明

`v1.2/` 是对 `v1.0/` 的轻量化重构实验版：界面层改为 `HTML + CSS + JavaScript`，Python 负责本地 HTTP 后端和伤害计算，桌面入口使用 `pywebview` 打开内嵌 WebView 窗口。目标是保留“一个软件窗口”的体验，同时去掉 PySide6 依赖，降低打包体积，并让 UI 维护更直观。

## 当前结构

- `desktop_app.py`：正式桌面软件入口，启动本地后端并创建内嵌 WebView 窗口。
- `server.py`：本地 HTTP 服务和 API 定义，使用 Python 标准库 `http.server`，可单独作为调试入口。
- `web/index.html`：Web 前端页面结构。
- `web/styles.css`：Web 前端样式。
- `web/app.js`：前端交互、表单收集、API 调用、结果渲染。
- `gui/config.py`：沿用 v1.0 的配置 dataclass。
- `gui/resources.py`：v1.2 资源路径，已适配源码运行和 PyInstaller `_MEIPASS`。
- `gui/services.py`：沿用 v1.0 的服务层，仍负责角色查询、绘卷查询、详情格式化、计算编排。
- `character.py`、`battle_op_state.py`、`damage_pipeline_skeleton.py`、`attack_order.py`、`buff_effect.py`、`combat_constants.py`：沿用原伤害计算核心。
- `equipment_parser.py`、`recommend_equipment.py`：沿用绘卷解析和推荐逻辑。
- `assets/avatars/`：角色头像目录，命名约定为 `S{角色ID}01.png`；缺失时回退到 `S0.png`。
- `presets/`：预设目录，当前用于保存 `character_presets.json`；目录内有 `.keep`，用于保证空目录也能进入打包产物。
- `datajson/`、`characters.csv`、`equipment_data.json`、`recommended.csv`、`buff_translation.csv`、`tribe_extracted.csv`、`local_translations.json`：运行所需数据。

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
- 批量计算并导出 summary，输出到 `output/`。
- 角色查询。
- 绘卷查询。
- 角色详情展示。
- 总览模块，可点击敌我位置跳转到对应参数卡片。
- 总览模块已并入 `伤害计算` 子页面；周擂台模式可切换敌方 1-3 波，前端会保存三套敌方参数。
- 角色预设模块，当前单次编辑一个角色，支持六维加成、五张绘卷、未拥有标记、简略/详细绘卷展示，并保存到 `presets/character_presets.json`。
- 擂台预设模块支持敌方六维、盾数量 3/5、气质贴图，并保存到 `presets/arena_presets.json`。
- 复灵预设模块会初步解析上级目录的 `复灵敌人数据06-19.lua`，输出到 `presets/vs/vs_enemy_data_06-19.json`。
- 复灵模拟模块支持载入当前复灵/敌我参数后按“计算本回合 / 过回合”交替推进：计算不会自动增加回合，过回合会继承敌方剩余 HP；仅在当前血条清空且存在下一血条时切换血条，否则禁用该敌方。
- 复灵模拟中的我方技能需要手动点击才会生效；导入模拟时会清空原我方参数页的技能顺序，避免每回合自动释放三个技能。技能按钮会把可解析的技能效果写入当前敌我 buff/P 点状态。
- 周擂台求解支持“只考虑对应擂台加成 Type”开关，默认开启；每波答案候选只返回溢出大于 `-1000` 的角色，避免 0 伤害角色占据结果。
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

- 把 `gui/services.py` 移出 `gui/`，改名为 `backend/services.py`，避免桌面壳继续带旧 GUI 命名。
- 将 `DamageCalculatorService` 拆成角色服务、绘卷服务、计算服务、翻译服务。
- 给 `/api/calculate`、`/api/equipment`、`/api/characters` 添加最小自动化 smoke test。
- 前端补角色详情编辑与保存。
- 前端 buff 输入改成可搜索下拉，同时复用后端 subID API。
- 批量 summary 增加浏览器下载入口，而不是只显示本地路径。
- 继续完善复灵模拟状态机：当前已支持手动技能写入、tag 乘区、剩余 HP 继承和基础血条切换；后续还需要补完整异常结界图标状态、敌方技能触发条件、EX 清除 buff 规则和技能 CD 回合递减。
- 周擂台求解目前以“终符 + 三技能 + 推荐绘卷”的单角色模板遍历，后续如果要模拟多角色/多回合组合，需要单独扩展搜索器。
- 拟真计算目前按已算出的每 hit 期望值做随机重算，后续如果需要逐 hit 扣血完全拟真，需要下沉到 `damage_pipeline_skeleton.py` 的计算过程内部。

中期优化：

- 将 `web/app.js` 拆成 `api.js`、`forms.js`、`render_result.js`、`query_pages.js`。
- 为绘卷查询的命中 buff 添加更明确的高亮。
- 给计算详情增加 trace 视图，解释每个乘区来源。
- 增加启动时资源完整性检查，提示缺失的 CSV/JSON。
- 将输出文件统一放到 `output/`，并避免污染源码根目录。

长期优化：

- 如果 v1.2 桌面壳稳定，可以逐步废弃 PySide6 版打包流程。
- 如果 `pywebview` 打包兼容性不稳定，可以退回 `server.py --browser-mode app` 的外部浏览器 app 窗口方案；如果体积允许，也可以重新评估 PySide6。
- 如果仍要进一步压缩体积，可尝试只保留 `.pyc` 或将数据资源压缩加载，但优先级低于功能稳定。
