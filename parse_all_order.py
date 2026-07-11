import os
import re
import json
from typing import Optional, Tuple

# =========================
# 配置区
# =========================

# 文本文件路径（你的段落文本）
TXT_PATH = r"./段落260308.txt"

# datajson 文件夹路径
DATAJSON_DIR = r"./datajson"

# 是否覆盖写回
WRITE_BACK = True

# 是否在写入前创建 .bak 备份
MAKE_BACKUP = True


# 第二列映射到 attack_skills 的 key
ATTACK_SKILL_MAP = {
    1: "1c",
    2: "2c",
    3: "1",
    4: "2",
    7: "5",
}


def parse_line(line: str) -> Optional[Tuple[str, int, int, str]]:
    """
    解析一行，例如：
    {12040,1,3,"1212111311141516"}

    返回:
        (char_id, attack_type_num, strengthen_level, all_order_str)
    """
    line = line.strip().rstrip(",").strip()
    if not line:
        return None

    pattern = r'^\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]*)"\s*\}$'
    m = re.match(pattern, line)
    if not m:
        return None

    char_id = m.group(1)
    attack_type_num = int(m.group(2))
    strengthen_level = int(m.group(3))
    all_order_str = m.group(4)

    return char_id, attack_type_num, strengthen_level, all_order_str


def update_json_file(
    json_path: str,
    attack_type_num: int,
    strengthen_level: int,
    all_order_str: str,
) -> bool:
    """
    更新单个 json 文件。
    成功返回 True，失败返回 False。
    """
    if attack_type_num not in ATTACK_SKILL_MAP:
        print(f"  [跳过] 未知第二列类型: {attack_type_num} | 文件: {json_path}")
        return False

    attack_skill_key = ATTACK_SKILL_MAP[attack_type_num]
    all_order_key = f"all_order_{strengthen_level}"
    all_order_value = f"{all_order_str}g"

    if not os.path.exists(json_path):
        print(f"  [缺失] 文件不存在: {json_path}")
        return False

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [失败] 读取 JSON 出错: {json_path} | {e}")
        return False

    try:
        attack_skills = data.setdefault("attack_skills", {})
        if attack_skill_key not in attack_skills:
            print(f"  [缺失] attack_skills['{attack_skill_key}'] 不存在 | 文件: {json_path}")
            return False

        skill_part = attack_skills[attack_skill_key]
        global_attributes = skill_part.setdefault("global_attributes", {})
        old_value = global_attributes.get(all_order_key, None)
        global_attributes[all_order_key] = all_order_value

        if WRITE_BACK:
            if MAKE_BACKUP:
                backup_path = json_path + ".bak"
                if not os.path.exists(backup_path):
                    with open(backup_path, "w", encoding="utf-8") as bf:
                        json.dump(data, bf, ensure_ascii=False, indent=4)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        print(
            f"  [成功] {os.path.basename(json_path)} | "
            f"{attack_skill_key} -> {all_order_key} = {all_order_value} "
            f"(旧值: {old_value})"
        )
        return True

    except Exception as e:
        print(f"  [失败] 写入 JSON 出错: {json_path} | {e}")
        return False


def main():
    if not os.path.exists(TXT_PATH):
        print(f"[错误] 文本文件不存在: {TXT_PATH}")
        return

    if not os.path.isdir(DATAJSON_DIR):
        print(f"[错误] datajson 文件夹不存在: {DATAJSON_DIR}")
        return

    total = 0
    success = 0
    skipped = 0

    with open(TXT_PATH, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            parsed = parse_line(line)
            if parsed is None:
                print(f"[跳过] 无法解析行: {line}")
                skipped += 1
                continue

            char_id, attack_type_num, strengthen_level, all_order_str = parsed
            total += 1

            json_path = os.path.join(DATAJSON_DIR, f"{char_id}.json")
            ok = update_json_file(
                json_path=json_path,
                attack_type_num=attack_type_num,
                strengthen_level=strengthen_level,
                all_order_str=all_order_str,
            )
            if ok:
                success += 1
            else:
                skipped += 1

    print("\n=== 处理完成 ===")
    print(f"总条目: {total}")
    print(f"成功:   {success}")
    print(f"跳过:   {skipped}")


if __name__ == "__main__":
    main()