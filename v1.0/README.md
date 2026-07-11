# lwMAA v1.1 维护说明

这份 README 面向后续继续维护 `v1.0/` 目录的人，也面向下一个接手的 Codex 对话。

当前继续上下文命令：

```powershell
codex resume 019d56fc-e2db-7220-ac0b-7fcd329a9b9b
```

## 当前状态

`v1.0/` 是当前实际维护目录。虽然目录名仍叫 `v1.0`，但 GUI 标题和功能状态按 `v1.1` 维护。

当前版本已经从早期单文件 GUI 拆成了 GUI 包 + 计算核心 + 数据资源的结构：

- GUI 入口仍是 `gui_app.py`，但只负责转发到 `gui.main.main()`。
- GUI 主体在 `gui/` 下，包括主窗口、页面组件、服务层和资源。
- 已实装绘卷解析、国服绘卷名合并、D 绘卷解析、推荐绘卷、角色查询、绘卷查询、角色详情页。
- 已实装场地 buff、绘卷 ID 14/15 伤害加成、部分高 ID / type 条件 buff、敌方单体/群体抗性与仇恨相关修正。
- 批量 summary 已集成 `trans_sum.py` 的翻译逻辑，不需要先生成 `batch_summary.csv` 再手动执行转换。
- 打包主入口是 `v1.0/lw_damage_calculator.spec`，不建议继续使用旧的超长 `pyinstaller --add-data ... gui_app.py` 命令。

## 目录结构

主要入口与 GUI：

- `gui_app.py`：兼容入口，内容很短，只调用 `gui.main.main()`。
- `gui/main.py`：创建 `QApplication`，设置 Windows 风格，创建并显示 `MainWindow`。
- `gui/main_window.py`：主窗口、Tab 装配、计算过程页、结果页、批量 summary 导出。
- `gui/widgets.py`：敌方参数、我方参数、buff 表、quality、场地 buff、绘卷行、角色查询、绘卷查询、角色详情等 UI 组件。
- `gui/services.py`：GUI 和底层计算之间的服务层，负责读取角色/绘卷/翻译数据、组装计算输入、执行计算、查询和批量导出。
- `gui/config.py`：GUI 配置 dataclass，例如敌方槽位、我方槽位、场地 buff、流程配置。
- `gui/resources.py`：资源路径辅助。
- `gui/resources/`：GUI 资源，目前包含 `app.ico` 和 `startup_notice.json`。

战斗与伤害计算核心：

- `character.py`：角色实例、面板、buff、结界、角色管理器。
- `battle_op_state.py`：攻击前状态处理，包括技能、换位、开盾、开 p、攻击前后 buff 等。
- `damage_pipeline_skeleton.py`：主要伤害计算流程，包含段落/hit 计算、属性/弹种/场地/绘卷/特攻/命中会心/敌方抗性等乘区。
- `attack_order.py`：前排攻击顺序、速度修正、攻击段落顺序解析。
- `buff_effect.py`：基础 buff/effect 解析映射。
- `combat_constants.py`：通用常量与 subID 归一化辅助。
- `debug_single_case.py`：单例 debug 工具，输出 JSON，不应影响 GUI 主流程。

绘卷相关：

- `equipment_parser.py`：解析 `绘卷buff03-26.txt`、`绘卷buff04-04国服.txt`、`D绘卷.txt`，输出 `equipment_data.json`。
- `recommend_equipment.py`：计算角色推荐绘卷，输出 `attack5_candidates.csv` 和 `recommended.csv`。
- `equipment_data.json`：GUI 和计算流程读取的绘卷结构化数据。
- `recommended.csv`：每个角色推荐的 5 张绘卷结果。
- `attack5_candidates.csv`：终符绘卷候选和提升估算中间结果。
- `绘卷buff03-26.txt`：早期原始绘卷数据。
- `绘卷buff04-04国服.txt`：国服绘卷数据，用于更新名称和补充国服特供绘卷。
- `D绘卷.txt`：D 绘卷数据。D 绘卷只参与 LW/终符推荐，不参与前四张符卡推荐。

数据与翻译：

- `datajson/`：角色 JSON 数据源。
- `characters.csv`：角色索引和名称数据。
- `tribe_extracted.csv`：tribe/特攻对应文本。
- `buff_translation.csv`：buff ID、subID、target 等翻译和说明。
- `local_translations.json`：本地补充中文翻译表。
- `LW全技能总览.xlsx`：技能/buff 翻译和说明参考源；当前打包规格中为了减小体积已排除 `openpyxl`，运行时优先使用 CSV/JSON 数据。
- `presets/`：预设输入。

生成物和临时目录：

- `build/`：PyInstaller 构建中间产物，可删除后重建。
- `dist/`：PyInstaller 输出目录，可删除后重建。
- `__pycache__/`：Python 缓存，可删除。
- `batch_summary.csv`：批量计算导出结果，属于运行生成物。
- `*.png`：部分是调试截图，不属于核心运行依赖。

## 当前 GUI 页面

主界面目前大致包含这些页面：

- 敌方参数：选择敌方位置 0/1/2 的角色、quality、buff、护盾等。
- 我方参数：选择我方前后排角色、攻击类型、技能释放、开 p 数、开盾数量、目标敌人、五张绘卷。
- 计算过程：单次计算、批量计算并导出 summary、场地 buff、敌我当前启用状态、可收起的 JSON/明细显示。
- 最终结果：按总计、敌方 0、敌方 1、敌方 2 分表展示伤害明细。
- 角色查询：按 type、世界群、终符属性、终符弹种、特攻、转生等筛选，可排序，可进入角色详情。
- 绘卷查询：按 ID、星级、种类、属性、buff ID/subID/value/type 等筛选，buff 命中项会高亮。
- 角色详情：展示基础属性、技能、特性、攻击类型、段落 hit、特攻、buff 和效果翻译。

## 主计算流程

当前主流程可按下面顺序理解：

1. GUI 收集敌我双方配置、操作配置、buff、quality、场地 buff、绘卷。
2. `gui.services.DamageCalculatorService` 将 GUI 配置转换成底层角色实例和操作状态。
3. `character.py` 创建 9 个位置的角色实例：敌方 0-2，我方前排 0-2，我方后排 3-5。
4. `battle_op_state.py` 处理攻击前操作，例如技能、换位、开盾、开 p、攻击前 buff。
5. `attack_order.py` 计算我方前排攻击顺序。
6. `damage_pipeline_skeleton.py` 按攻击者、段落、hit、目标敌人执行伤害计算。
7. 伤害计算会综合面板、buff 层数、属性相性、弹种/属性增伤减伤、绘卷、场地 buff、特攻、命中、会心、敌方仇恨和单体/群体抗性等。
8. 三名我方前排角色执行完后，GUI 汇总结果并导出 summary。

目标敌人逻辑注意点：

- 如果目标敌人不存在，会从左到右寻找第一个实际存在的敌方。
- 如果敌方无人，伤害返回 0。

技能逻辑注意点：

- 我方参数的 skills 为空时表示不开技能，不应默认按 0、1、2 顺序释放。
- GUI 支持自定义多角色技能释放顺序，避免固定按位置 0、1、2。

绘卷逻辑注意点：

- 每个我方角色最多装备 5 张绘卷，对应两张 1 符、两张 2 符、一张终符。
- 扩散和集中，即 `1c`、`2c`，不能装备绘卷。
- 前四张符卡目前主要考虑面板加成；终符推荐同时考虑面板、属性增伤、弹种增伤。
- ID 14/15 的同 ID/subID 增伤按加算处理，然后进入对应乘区。
- D 绘卷只在 LW/终符推荐中考虑。

## 本地运行

在 `v1.0` 目录下运行：

```powershell
python gui_app.py
```

如果从上一级 `v1.1_test/` 运行，可能会误用上一级残留的旧文件。后续维护建议固定进入 `v1.0/` 后再运行和打包。

## 数据刷新

重新解析绘卷：

```powershell
python equipment_parser.py
```

重新生成推荐绘卷：

```powershell
python recommend_equipment.py
```

通常在修改这些文件后需要刷新：

- `绘卷buff03-26.txt`
- `绘卷buff04-04国服.txt`
- `D绘卷.txt`
- `equipment_parser.py`
- `recommend_equipment.py`
- 与绘卷 buff、type、属性、弹种、面板相关的计算逻辑

刷新后重点检查：

- `equipment_data.json`
- `attack5_candidates.csv`
- `recommended.csv`
- GUI 中绘卷查询和推荐按钮

## 打包流程

推荐使用干净 venv 打包，不建议直接在 `conda base` 中打包。之前在 conda 环境下出现过 `DLL load failed while importing QtWidgets` 一类问题，干净 venv 更稳定。

在 `v1.0` 目录下首次创建打包环境：

```powershell
conda deactivate
C:\Users\Deity4113\anaconda3\python.exe -m venv .buildvenv
.\.buildvenv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-build.txt -i https://mirrors.aliyun.com/pypi/simple/
python -m PyInstaller --noconfirm --clean lw_damage_calculator.spec
```

已经创建过 `.buildvenv` 时：

```powershell
.\.buildvenv\Scripts\activate
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean lw_damage_calculator.spec
```

输出位置：

```text
dist/lw_damage_calculator/lw_damage_calculator.exe
```

注意事项：

- 当前是 `onedir` 打包，不是单文件打包。
- 不要把 `lw_damage_calculator.exe` 单独复制出去运行。
- 分发时应压缩整个 `dist/lw_damage_calculator/` 文件夹。
- 重新打包前要关闭已经运行的 `lw_damage_calculator.exe`。
- 当前 `.spec` 已排除大量 Qt QML/WebEngine/PDF/3D/Charts/SQL/Multimedia 等模块来减小体积。
- `plugins/styles/qmodernwindowsstyle.dll` 需要保留，否则打包后 UI 会退化成很简陋的样式。
- 当前 `.spec` 关闭了 UPX，目的是降低 PySide6/Qt DLL 在 Windows 下加载失败的风险。
- 最近一次优化后的目标体积约为 100-150 MB 量级；如果重新变成 400-500 MB，优先检查 `.spec` 是否误用了上一级旧 spec 或是否把 QML/WebEngine/无关依赖重新收进去了。

打包后检查样式插件：

```powershell
Get-ChildItem .\dist\lw_damage_calculator\_internal\PySide6\plugins\styles
```

打包后检查体积：

```powershell
Get-ChildItem .\dist\lw_damage_calculator -Recurse | Measure-Object Length -Sum
```

## 打包依赖

`requirements-build.txt` 是打包环境依赖，不是完整生产锁定文件。当前内容应保持尽量小，避免把 pandas、matplotlib、scipy、pygame 等无关大依赖带入打包环境。

当前 `.spec` 中显式排除了：

- `numpy`
- `openpyxl`
- `pandas`
- `PIL`
- `pygame`
- `scipy`
- `lxml`
- 大量不使用的 PySide6 Qt 模块

如果后续代码重新在运行时强依赖这些库，必须同步修改 `.spec` 和 `requirements-build.txt`，否则源码运行可能正常，打包后会报缺模块。

## 验证命令

语法检查：

```powershell
python -m py_compile gui\main.py gui\main_window.py gui\widgets.py gui\services.py gui\config.py character.py battle_op_state.py damage_pipeline_skeleton.py equipment_parser.py recommend_equipment.py
```

基础手动验收建议：

- `python gui_app.py` 能打开主界面。
- 敌方参数和我方参数页没有乱码。
- quality 的归零按钮正常。
- 我方 skills 为空时不会自动开技能。
- 单次计算能跑通。
- 批量计算并导出 summary 能生成中文列名。
- 最终结果能按总计、敌方 0、敌方 1、敌方 2 分表显示。
- 角色查询能筛选、排序、进入详情。
- 绘卷查询能按 buff ID/subID/value/type 交叉筛选。
- 推荐绘卷按钮能填入推荐结果。
- 打包后的 exe 打开后 UI 样式不是简陋 fallback 样式。

## 已知风险

- `gui/services.py` 和 `gui/widgets.py` 仍然偏大，后续继续加功能会增加维护成本。
- 部分中文名称和 buff 文本来自本地翻译表，仍可能不完整或不一致。
- `LW全技能总览.xlsx` 是参考源，但打包产物不应依赖运行时读取 xlsx；优先维护 CSV/JSON 派生数据。
- `dist/`、`build/`、`batch_summary.csv` 是生成物，容易污染源码目录。后续如纳入版本管理，应明确忽略或单独归档。
- 上一级 `v1.1_test/` 目录仍有旧版代码和旧 spec，容易误运行。后续建议统一入口，或明确标记上一级为历史/辅助文件。
- GUI 布局经过多轮手工压缩和调宽，后续改动最好做截图验收，避免表格宽度、行高、折叠区样式回退。

## 后续优化方向

优先级较高：

- 拆分 `gui/services.py`：建议拆成角色索引/查询服务、绘卷服务、计算编排服务、翻译格式化服务。
- 拆分 `gui/widgets.py`：建议把敌我参数页、查询页、详情页、通用表格控件分文件维护。
- 建立最小 smoke test：覆盖目标敌人 fallback、skills 为空、绘卷推荐、场地 buff、敌方单体/群体抗性、batch summary 列名。
- 固化打包验证：每次改 `.spec` 后检查体积、样式插件、启动、单次计算和批量导出。
- 清理上一级旧入口和旧 spec 的歧义，避免用户在 `v1.1_test/` 和 `v1.0/` 间误运行。

中期优化：

- 将 buff 翻译、ID/subID 映射、type 映射、属性/弹种映射统一集中，减少 GUI 和计算层重复定义。
- 为绘卷推荐建立可解释输出，记录每张推荐绘卷的面板提升、属性增伤、弹种增伤和最终倍率。
- 将角色详情中的技能/攻击段落翻译和计算层 effect 解析共用同一套格式化函数，避免展示和计算不一致。
- 把生成物移动到 `output/` 或 `generated/`，减少根目录混乱。
- 对 `equipment_parser.py` 增加解析数量、重复 ID、D 绘卷 subID、国服名称覆盖的检查输出。

长期优化：

- 将战斗流程改成更明确的阶段流水线，例如“构建状态 -> 执行操作 -> 攻击前 -> 段落计算 -> hit 计算 -> 攻击后 -> 汇总”。
- 为核心伤害公式建立可回放的 JSON trace，方便解释为什么某个绘卷或 buff 生效。
- 给 GUI 添加自动化截图或关键控件存在性检查，降低后续布局改动回归风险。
- 如果继续压缩包体积，可考虑更小的 Qt 发行方式或换轻量 GUI，但这会带来较大迁移成本；当前 PySide6 onedir 方案优先保持稳定。

## 给下一个 Codex 的接手建议

接手时先做三件事：

1. 进入 `v1.0/`，不要先改上一级残留旧代码。
2. 先读 `gui/services.py`、`gui/widgets.py`、`damage_pipeline_skeleton.py` 的相关函数，再改 GUI 或计算链路。
3. 如果涉及绘卷或推荐结果，修改后必须重新运行 `equipment_parser.py` 和 `recommend_equipment.py`，并检查 `equipment_data.json`、`recommended.csv`。

如果用户反馈打包体积或 UI 样式问题，优先检查：

- 当前是否在 `v1.0/` 下执行打包。
- 是否使用的是 `v1.0/lw_damage_calculator.spec`。
- `dist/lw_damage_calculator/_internal/PySide6/plugins/styles/` 是否存在 `qmodernwindowsstyle.dll`。
- `.spec` 中 Qt blocklist 是否仍然生效。
- 运行的 exe 是否是刚刚重新打包出来的，不是旧进程或旧目录。
