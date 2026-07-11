import json
import csv
import os
from collections import defaultdict

def count_tribe_occurrences(json_folder):
    """
    统计JSON文件夹中所有tribe数字的出现次数
    
    参数:
    json_folder: JSON文件所在文件夹路径
    
    返回:
    tribe_count_dict: {tribe_id: 出现次数} 的字典
    """
    # 初始化计数器
    tribe_count = defaultdict(int)
    processed_files = 0
    total_characters = 0
    
    # 检查文件夹是否存在
    if not os.path.exists(json_folder):
        print(f"❌ 错误：文件夹 {json_folder} 不存在")
        return None
    
    # 遍历文件夹中的所有文件
    print(f"正在扫描文件夹: {json_folder}")
    for filename in os.listdir(json_folder):
        # 只处理JSON文件
        if filename.endswith('.json'):
            file_path = os.path.join(json_folder, filename)
            try:
                # 读取JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取character_info中的tribe列表
                if 'character_info' in data and 'tribe' in data['character_info']:
                    tribe_list = data['character_info']['tribe']
                    # 统计每个tribe数字的出现次数
                    for tribe_id in tribe_list:
                        # 确保tribe_id是整数类型
                        tribe_count[int(tribe_id)] += 1
                    
                    processed_files += 1
                    total_characters += 1
                    character_name = data['character_info'].get('name', '未知角色')
                    print(f"✅ 处理文件: {filename} | 角色: {character_name} | Tribe列表: {tribe_list}")
                else:
                    print(f"⚠️ 警告：文件 {filename} 缺少tribe数据，已跳过")
            
            except json.JSONDecodeError:
                print(f"⚠️ 警告：文件 {filename} 不是有效的JSON格式，已跳过")
            except Exception as e:
                print(f"⚠️ 警告：处理文件 {filename} 时出错: {str(e)}")
    
    # 输出统计信息
    print(f"\n📊 JSON文件处理统计:")
    print(f"- 处理的JSON文件数: {processed_files}")
    print(f"- 处理的角色数: {total_characters}")
    print(f"- 统计到的tribe类型数: {len(tribe_count)}")
    
    # 按tribe ID排序显示统计结果
    sorted_tribe_count = dict(sorted(tribe_count.items()))
    print(f"\n🔍 Tribe数字出现次数统计（前20个）:")
    for i, (tribe_id, count) in enumerate(sorted_tribe_count.items()):
        if i < 20:
            print(f"   Tribe ID {tribe_id:4d} | 出现次数: {count}")
        else:
            print(f"   ... 还有 {len(sorted_tribe_count) - 20} 个tribe类型未显示")
            break
    
    return sorted_tribe_count

def update_tribe_csv(csv_file, tribe_count, output_file):
    """
    将tribe统计次数添加到CSV文件中
    
    参数:
    csv_file: 原始的tribe_extracted.csv文件路径
    tribe_count: tribe数字出现次数字典
    output_file: 更新后的CSV文件路径
    """
    # 读取原始CSV文件
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            csv_reader = csv.DictReader(f)
            rows = list(csv_reader)
        
        # 检查必要列是否存在
        if 'ID' not in csv_reader.fieldnames:
            print(f"❌ 错误：CSV文件缺少 'ID' 列")
            return False
        
        # 为每一行添加count列
        updated_rows = []
        for row in rows:
            try:
                # 确保ID转换为整数，避免字符串匹配问题
                tribe_id = int(row['ID'])
                # 获取该tribe的出现次数，默认为0
                count = tribe_count.get(tribe_id, 0)
                # 确保count是整数类型
                row['count'] = int(count)
                updated_rows.append(row)
            except ValueError:
                # 处理ID无法转换为整数的情况
                print(f"⚠️ 警告：行 {row} 的ID不是有效数字，已跳过")
                continue
        
        # 写入更新后的CSV文件
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            # 获取更新后的列名（添加count列）
            fieldnames = csv_reader.fieldnames + ['count']
            csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # 写入表头
            csv_writer.writeheader()
            
            # 写入数据
            csv_writer.writerows(updated_rows)
        
        print(f"\n✅ CSV文件更新完成！")
        print(f"- 原始文件: {csv_file}")
        print(f"- 输出文件: {output_file}")
        print(f"- 处理行数: {len(updated_rows)}")
        print(f"- 新增列: 'count' (tribe出现次数)")
        
        # 显示前10行预览（修复格式符错误）
        print(f"\n📋 更新后数据预览（前10行）:")
        for i in range(min(10, len(updated_rows))):
            row = updated_rows[i]
            # 使用%s兼容所有类型，或显式转换为整数
            tribe_id = int(row['ID']) if row['ID'].isdigit() else row['ID']
            count_val = int(row['count']) if str(row['count']).isdigit() else row['count']
            print(f"ID:{tribe_id:3} | {row['tribe_name']:<10} | 出现次数: {count_val:3}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ 错误：找不到CSV文件 {csv_file}")
        return False
    except Exception as e:
        print(f"❌ 错误：{str(e)}")
        return False

# 主程序执行
if __name__ == "__main__":
    # 配置文件路径（根据实际情况修改）
    JSON_FOLDER = "datajson"                # JSON文件所在文件夹
    INPUT_CSV = "tribe_extracted.csv"       # 原始的tribe CSV文件
    OUTPUT_CSV = "tribe_extracted_with_count.csv"  # 更新后的CSV文件
    
    # 步骤1：统计JSON文件中的tribe出现次数
    tribe_count = count_tribe_occurrences(JSON_FOLDER)
    
    if tribe_count:
        # 步骤2：更新CSV文件，添加count列
        success = update_tribe_csv(INPUT_CSV, tribe_count, OUTPUT_CSV)
        
        if success:
            print(f"\n🎉 所有操作完成！最终文件: {OUTPUT_CSV}")
    else:
        print(f"\n❌ 处理失败，无法更新CSV文件")
