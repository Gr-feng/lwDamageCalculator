import csv
import re

def extract_tribe_data(input_file, output_file):
    """
    从tribe.txt文件提取数据并生成带ID的CSV文件
    
    参数:
    input_file: 输入的tribe.txt文件路径
    output_file: 输出的CSV文件路径
    """
    
    # 存储提取的数据
    tribe_data = []
    
    # 读取并解析文件
    print(f"正在读取文件: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 遍历每一行，从1开始计数作为ID
            for line_num, line in enumerate(lines, 1):
                # 去除首尾空白字符
                clean_line = line.strip()
                
                # 跳过空行
                if not clean_line:
                    continue
                
                # 使用正则表达式提取第一个{}内的内容
                # 匹配 {"内容",数字} 格式中的内容部分
                match = re.match(r'\{"([^"]+)"\s*,\s*\d+\}', clean_line)
                if match:
                    # 提取第一个值
                    tribe_name = match.group(1)
                    # 添加到数据列表 (ID, 名称)
                    tribe_data.append([line_num, tribe_name])
                    print(f"ID:{line_num:3d} | 提取内容: {tribe_name}")
                else:
                    print(f"警告：第{line_num}行格式不匹配，已跳过 | 内容: {clean_line}")
        
        # 写入CSV文件
        print(f"\n正在写入CSV文件: {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # 创建CSV写入器
            csv_writer = csv.writer(csvfile)
            
            # 写入表头
            csv_writer.writerow(['ID', 'tribe_name'])
            
            # 写入数据行
            csv_writer.writerows(tribe_data)
        
        # 输出统计信息
        print(f"\n✅ 处理完成！")
        print(f"- 总读取行数: {len(lines)}")
        print(f"- 成功提取数据行数: {len(tribe_data)}")
        print(f"- 输出文件: {output_file}")
        print(f"- 文件编码: UTF-8 (带BOM)，支持Excel正常显示中文")
        
        return tribe_data
        
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {input_file}")
        return None
    except Exception as e:
        print(f"❌ 错误：{str(e)}")
        return None

# 主程序执行
if __name__ == "__main__":
    # 配置文件路径（根据实际情况修改）
    INPUT_FILE = "tribe.txt"       # 输入的tribe文件
    OUTPUT_FILE = "tribe_extracted.csv"  # 输出的CSV文件
    
    # 调用函数提取数据
    result = extract_tribe_data(INPUT_FILE, OUTPUT_FILE)
    
    # 如果提取成功，显示前10条数据预览
    if result:
        print(f"\n📋 数据预览（前10条）:")
        for i in range(min(10, len(result))):
            print(f"ID:{result[i][0]:3d} | {result[i][1]}")
