import csv
from pathlib import Path


INPUT_TXT = "转生符卡60127483.txt"
OUTPUT_CSV = "转生符卡60127483_parsed.csv"


def split_top_level_fields(s: str):
    """
    只在最外层按逗号切分。
    忽略：
    - 双引号内的逗号
    - 花括号/方括号内的逗号
    """
    fields = []
    buf = []

    brace_depth = 0
    bracket_depth = 0
    in_string = False
    escape = False

    for ch in s:
        if in_string:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            buf.append(ch)
        elif ch == "{":
            brace_depth += 1
            buf.append(ch)
        elif ch == "}":
            brace_depth -= 1
            buf.append(ch)
        elif ch == "[":
            bracket_depth += 1
            buf.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            buf.append(ch)
        elif ch == "," and brace_depth == 0 and bracket_depth == 0:
            fields.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)

    if buf:
        fields.append("".join(buf).strip())

    return fields


def clean_field(x: str):
    x = x.strip()
    if len(x) >= 2 and x[0] == '"' and x[-1] == '"':
        x = x[1:-1]
    return x


def parse_record_line(line: str):
    line = line.strip()
    if not line or line.startswith("--"):
        return None
    if not line.startswith("{"):
        return None

    # 去掉末尾逗号
    if line.endswith(","):
        line = line[:-1].rstrip()

    # 去掉最外层 {}
    if line.startswith("{") and line.endswith("}"):
        line = line[1:-1].strip()
    else:
        return None

    fields = split_top_level_fields(line)

    # 理论上至少 16 列：
    # 11个主字段 + 后置效果5组
    if len(fields) < 16:
        print(f"[跳过] 字段数量不足: {line[:120]}")
        return None

    row = {
        "编号": clean_field(fields[0]),
        "角色名": clean_field(fields[1]),
        "角色编号": clean_field(fields[2]),
        "所属转生强化ID": clean_field(fields[3]),
        "强化阶段": clean_field(fields[4]),
        "强化的符卡": clean_field(fields[5]),
        "强化内容": clean_field(fields[6]),
        "强化段落序号": clean_field(fields[7]),
        "强化后段落ID": clean_field(fields[8]),
        "未知": clean_field(fields[9]),
        "强化消耗": clean_field(fields[10]),
        "强化后前后置效果1": clean_field(fields[11]),
        "强化后前后置效果2": clean_field(fields[12]),
        "强化后前后置效果3": clean_field(fields[13]),
        "强化后前后置效果4": clean_field(fields[14]),
        "强化后前后置效果5": clean_field(fields[15]),
    }
    return row


def main():
    input_path = Path(INPUT_TXT)
    output_path = Path(OUTPUT_CSV)

    rows = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = parse_record_line(line)
            if rec is not None:
                rows.append(rec)

    fieldnames = [
        "编号",
        "角色名",
        "角色编号",
        "所属转生强化ID",
        "强化阶段",
        "强化的符卡",
        "强化内容",
        "强化段落序号",
        "强化后段落ID",
        "未知",
        "强化消耗",
        "强化后前后置效果1",
        "强化后前后置效果2",
        "强化后前后置效果3",
        "强化后前后置效果4",
        "强化后前后置效果5",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"完成，共导出 {len(rows)} 行 -> {output_path}")


if __name__ == "__main__":
    main()