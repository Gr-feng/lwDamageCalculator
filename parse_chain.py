def parse_chain_file(content):
    """解析连锁角色文件（chain类型），正确处理键值分行的格式"""
    lines = content.strip().split('\n')
    data = {}
    
    # 确保文件至少有两行有效内容
    if len(lines) < 2:
        return data
    
    # 处理第一行：提取键名（格式为 0:chain_character）
    first_line = lines[0].strip()
    if ':' not in first_line:
        return data
    
    # 拆分第一行，获取真正的键名（如 chain_character）
    _, key = first_line.split(':', 1)
    key = key.strip()
    
    # 处理第二行：提取数字列表
    second_line = lines[1].strip()
    if not second_line:
        return data
    
    # 转换为整数列表
    try:
        data[key] = list(map(int, second_line.split(',')))
    except ValueError:
        # 转换失败时保留原始字符串
        data[key] = second_line
    
    return data

# 测试示例
if __name__ == "__main__":
    # 模拟你的文件内容
    test_content = """0:chain_character
1009,1037,1025,1003,1010,1015,1038,1039,1020,1026,1005,1011,1032,1030,1033,1034,1035,1018,1024,1029,1042,1048,1044,1095,1084,1054,1052,1053,1092,1069,1089,1091,1083,1066,2002,1058,1085,1087,1080,1076,1043,1120,1040,1125,7073"""
    
    result = parse_chain_file(test_content)
    print(result)
    # 输出结果：{'chain_character': [1009, 1037, 1025, ..., 7073]}
