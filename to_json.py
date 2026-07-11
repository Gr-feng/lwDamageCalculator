import os
import re
from pathlib import Path
import json
# 导入子文件的解析函数（确保5个解析文件与主文件同级）
from parse_chain import parse_chain_file
from parse_cos import parse_cos_file
from parse_skill import parse_skill_file
from parse_attack import parse_attack_file
from parse_unit import parse_unit_file

# 验证内置json模块，排除重名问题
print("✅ JSON模块路径：", json.__file__)

# ===================== 精准识别角色编号+数据类型 =====================
DATA_TYPES = [
    'chain', 'cos', 'skill', 'unit',
    '1c', '2c',
    '1', '2', '5'
]

def get_file_type_and_id(file_name):
    """精准提取角色编号和数据类型，支持末尾数字类型（如100255→10025+5）"""
    # 清理文件名：移除.txt后缀和链接参数（?&后面的内容）
    clean_name = re.sub(r'\.txt|\?.*$|&.*$', '', file_name)
    
    # 方案1：匹配字符串类型/复合数字类型（cos/chain/1c等）
    for data_type in DATA_TYPES:
        if data_type in ['1', '2', '5']:
            continue  # 跳过纯数字类型，优先匹配其他类型
        pattern = re.compile(r'(\d+)\s*' + re.escape(data_type), re.I)
        match = pattern.search(clean_name)
        if match:
            return match.group(1), data_type.lower()
    
    # 方案2：匹配末尾纯数字类型（1/2/5）—— 核心适配场景
    num_type_pattern = re.compile(r'(\d+)([125])$')
    num_match = num_type_pattern.search(clean_name)
    if num_match:
        return num_match.group(1), num_match.group(2)
    
    # 无有效匹配时返回None
    return None, None

# ===================== 主解析逻辑（分发+生成文件） =====================
def parse_lw_wiki_folder(folder_path, output_folder):
    all_character_data = {}  # 存储所有角色数据，key=角色编号
    
    # 遍历源文件夹所有文件（跳过子文件夹）
    for file_path in Path(folder_path).iterdir():
        if file_path.is_dir():
            continue
        file_name = file_path.name
        
        # 提取角色编号和文件类型
        char_id, file_type = get_file_type_and_id(file_name)
        if not char_id or not file_type:
            print(f"❌ 跳过无效文件：{file_name[:50]}...（无有效编号/类型）")
            continue
        
        # 初始化当前角色的数据容器（避免覆盖已有数据）
        if char_id not in all_character_data:
            all_character_data[char_id] = {
                "character_info": {},    # unit类型：基础属性
                "chain_character": {},   # chain类型：连锁角色
                "costumes": {},          # cos类型：服装
                "skills": {},            # skill类型：主动技能
                "attack_skills": {}      # 1/1c/2/2c/5：攻击技能组
            }
        
        # 读取文件内容（兼容UTF-8编码，忽略异常字符）
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"❌ 读取失败：{file_name[:50]}... | 错误：{str(e)[:30]}")
            continue
        
        # 分发到对应解析函数，获取解析结果
        parsed_content = None
        if file_type == 'chain':
            parsed_content = parse_chain_file(content)
        elif file_type == 'cos':
            parsed_content = parse_cos_file(content)
        elif file_type == 'skill':
            parsed_content = parse_skill_file(content)
        elif file_type == 'unit':
            parsed_content = parse_unit_file(content)
        elif file_type in ['1', '1c', '2', '2c', '5']:
            parsed_content = parse_attack_file(content)
        else:
            print(f"❌ 跳过未适配类型：{file_name[:50]}... | 类型：{file_type}")
            continue
        
        # 将解析结果赋值到对应角色的对应字段
        if file_type == 'chain':
            all_character_data[char_id]["chain_character"] = parsed_content.get("chain_character", [])
        elif file_type == 'cos':
            all_character_data[char_id]["costumes"] = parsed_content["costumes"]
        elif file_type == 'skill':
            all_character_data[char_id]["skills"] = parsed_content["skills"]
        elif file_type == 'unit':
            all_character_data[char_id]["character_info"] = parsed_content["character_info"]
        elif file_type in ['1', '1c', '2', '2c', '5']:
            all_character_data[char_id]["attack_skills"][file_type] = parsed_content
        
        # 打印解析成功日志
        print(f"✅ 解析成功：{file_name[:50]}... → 角色{char_id} | 类型{file_type}")
    
    # 生成每个角色的独立JSON文件（无optimize_prefix，保留原始键名）
    for char_id, char_data in all_character_data.items():
        output_path = Path(output_folder) / f"{char_id}.json"
        # 写入JSON文件（ensure_ascii=False保留中文，indent=4格式化）
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(char_data, f, ensure_ascii=False, indent=4)
        print(f"📄 生成角色文件：{output_path.absolute()}")
    
    return all_character_data

# ===================== 执行入口（直接运行主文件即可） =====================
if __name__ == "__main__":
    # 配置路径（无需手动创建文件夹，脚本自动生成）
    SOURCE_FOLDER = "./lw/wiki"    # 源数据文件存放目录
    OUTPUT_FOLDER = "./datajson"   # 解析后JSON文件输出目录

    # 自动创建源文件夹和输出文件夹（不存在则创建）
    os.makedirs(SOURCE_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    # 检查源文件夹是否有文件，无文件则提示并退出
    source_files = [f for f in Path(SOURCE_FOLDER).iterdir() if f.is_file()]
    if not source_files:
        print(f"⚠️  源文件夹【{SOURCE_FOLDER}】中无任何文件！")
        print(f"💡 请将角色数据文件（如链接式txt）放入【{SOURCE_FOLDER}】后重新运行脚本")
        exit()

    # 开始解析流程
    print(f"\n🚀 开始解析源文件夹：{Path(SOURCE_FOLDER).absolute()}")
    print(f"🎯 解析结果将输出至：{Path(OUTPUT_FOLDER).absolute()}\n")
    all_character = parse_lw_wiki_folder(SOURCE_FOLDER, OUTPUT_FOLDER)
    
    # 解析完成后打印统计结果
    print(f"\n🎉 解析完成！共成功处理 {len(all_character)} 个角色")
    print(f"📁 所有角色JSON文件已保存至：{Path(OUTPUT_FOLDER).absolute()}")
    # 打印每个角色的核心信息
    for char_id in all_character:
        char_name = all_character[char_id]["character_info"].get("0:name", "未知名称")  # 保留原始键名前缀
        print(f"🔹 角色{char_id}：{char_name} | 对应文件：{char_id}.json")
