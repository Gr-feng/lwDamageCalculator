import os
import json
import csv

INPUT_DIR = "./datajson"
OUTPUT_CSV = "characters.csv"

TYPE_LABELS = {
    1: "防御",
    2: "支援",
    3: "回复",
    4: "干扰",
    5: "攻击",
    6: "技巧",
    7: "速攻",
    8: "破坏",
}


def extract_id_from_filename(filename: str) -> str:
    return os.path.splitext(filename)[0]


def main():
    rows = []

    if not os.path.isdir(INPUT_DIR):
        print(f"输入目录不存在: {INPUT_DIR}")
        return

    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(INPUT_DIR, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            char_info = data.get("character_info", {})

            char_id = extract_id_from_filename(filename)
            world_group = char_info.get("world_group", "")
            name = char_info.get("name", "")
            type_num = char_info.get("type", "")
            #break_type = char_info.get("break_type", "")
            type_label = TYPE_LABELS.get(type_num, "") if isinstance(type_num, int) else ""
            tribe = char_info.get("tribe", [])

            if isinstance(tribe, list):
                tribe_str = ",".join(str(x) for x in tribe)
            else:
                tribe_str = str(tribe)

            rows.append({
                "id": char_id,
                "world_group": world_group,
                "name": name,
                "type": type_num,
                #"break_type": break_type,
                "type_label": type_label,
                "tribe": tribe_str,
            })

        except Exception as e:
            print(f"处理失败: {filepath} -> {e}")

    def sort_key(row):
        try:
            return int(row["id"])
        except:
            return row["id"]

    rows.sort(key=sort_key)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "world_group", "name", "type", "type_label", "tribe"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"完成，共导出 {len(rows)} 条到 {OUTPUT_CSV}")


if __name__ == "__main__":
    main()