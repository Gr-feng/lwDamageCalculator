# backend 目录规划

当前 v1.2 仍以 `server.py` 作为 HTTP 入口；大型服务已从 `gui/services.py` 迁移到 `backend/services/calculator_service.py`，`gui/services.py` 只保留兼容导入。后续后端拆分建议按以下顺序迁移：

- `backend/api/`：拆出 `/api/*` 路由处理，减少 `server.py` 体积。
- `backend/core/`：已迁移 `character.py`、`battle_op_state.py`、`buff_effect.py`、`damage_pipeline_skeleton.py`、`attack_order.py`、`combat_constants.py`；根目录同名 wrapper 已删除，新增代码应统一使用 `backend.core.*`。
- `backend/parsers/`：已迁移 `vs_lua_parser.py`、`arena_excel_parser.py`、`unit_raw_parser.py`；根目录同名 wrapper 已删除，调试命令应使用 `python -m backend.parsers.xxx`。
- `backend/services/`：已迁移 `calculator_service.py` 和 `buff_text.py`。下一步按角色、绘卷、伤害计算、复灵、擂台继续拆分 `calculator_service.py`。

当前仍避免一次性拆散大型服务内部逻辑；优先保证导入路径稳定，再逐步把 API 和服务方法按领域拆小。
