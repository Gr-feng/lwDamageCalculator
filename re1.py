import json
import re
from pathlib import Path

TXT_PATH = Path("转生47200001.txt")   # 你的txt路径
DATA_DIR = Path("datajson")          # 角色json目录


def extract_ids_from_txt(txt_path: Path) -> set[int]:
    """
    提取尾字段为 '少女转生等级1' 的记录中的角色ID（第3列）。
    记录形如：
    {1,"博丽灵梦(L1)",1001,100,0,1,{"转生镜",1000},"{ \"1\" : 1 }","少女转生等级1"},
    """
    text = txt_path.read_text(encoding="utf-8")

    ids = set()

    # 按行处理最稳妥
    for raw_line in text.splitlines():
        line = raw_line.strip().rstrip(",")

        if not line:
            continue

        # 只处理尾部是 "少女转生等级1" 的记录
        if not re.search(r',"少女转生等级1"\}?$', line):
            continue

        # 提取前3个字段：{序号,"名字",ID,...
        m = re.match(r'^\{\s*\d+\s*,\s*"[^"]*"\s*,\s*(\d+)\s*,', line)
        if m:
            ids.add(int(m.group(1)))

    return ids


def update_re_field(json_path: Path) -> bool:
    """
    将 json 中 character_info.re 改为 True
    返回是否实际发生修改
    """
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "character_info" not in data:
        print(f"[跳过] 缺少 character_info: {json_path.name}")
        return False

    old_value = data["character_info"].get("re", None)

    # 按你的要求改为 True
    data["character_info"]["re"] = "True"

    changed = (old_value is not True)

    if changed:
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    return changed


def main():
    ids = extract_ids_from_txt(TXT_PATH)
    print(f"提取到 {len(ids)} 个需要处理的ID")

    updated = 0
    missing = 0

    for char_id in sorted(ids):
        json_path = DATA_DIR / f"{char_id}.json"

        if not json_path.exists():
            print(f"[缺失] {json_path}")
            missing += 1
            continue

        if update_re_field(json_path):
            print(f"[已修改] {json_path.name}")
            updated += 1
        else:
            print(f"[无需修改] {json_path.name}")

    print("\n处理完成")
    print(f"成功修改: {updated}")
    print(f"缺失文件: {missing}")


if __name__ == "__main__":
    main()