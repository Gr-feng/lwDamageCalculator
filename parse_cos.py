def parse_cos_file(content):
    """解析服装文件（cos类型），返回服装数量(count)和具体内容(costumes)"""
    lines = content.strip().split('\n')
    current_key, current_val = None, []
    raw_costume_data = {}  # 临时存储原始键值对
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if ':' in line:
            # 保存上一个键的内容
            if current_key:
                raw_costume_data[current_key] = '\n'.join(current_val)
            
            # 只拆分一次，避免重复拆分导致的错误
            parts = line.split(':', 1)
            # 确保拆分后有至少两个部分，避免索引越界
            if len(parts) < 2:
                current_key = None
                current_val = []
                continue
            
            # 提取键名和值
            key_part = parts[0].strip()
            value_part = parts[1].strip()
            
            # 正确提取真正的键名（如 costume_description1）
            current_key = value_part if key_part == '0' else value_part
            # 初始化当前值列表（处理值为空的情况）
            current_val = [] if current_key == value_part else [value_part]
        else:
            # 非键行，仅当current_key有效时追加内容
            if current_key:
                current_val.append(line)
    
    # 处理最后一个键值对
    if current_key and current_val:
        raw_costume_data[current_key] = '\n'.join(current_val)
    
    # 结构化整理服装信息
    costumes_dict = {}
    for key, value in raw_costume_data.items():
        if not key or not value:
            continue
        
        # 拆分前缀（类型）和序号
        prefix = ''
        num = ''
        for char in key:
            if char.isdigit():
                num += char
            else:
                prefix += char
        
        # 匹配服装名称/描述类型
        type_key = None
        if prefix == 'costume_description':
            type_key = 'description'
        elif prefix == 'costume_name':
            type_key = 'name'
        
        if not type_key or not num:
            continue
        
        # 按序号分组
        if num not in costumes_dict:
            costumes_dict[num] = {'name': '', 'description': ''}
        costumes_dict[num][type_key] = value
    
    # 转换为有序列表，并补充id
    sorted_costumes = []
    for num in sorted(costumes_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        sorted_costumes.append({
            'id': int(num) if num.isdigit() else 0,
            'name': costumes_dict[num]['name'],
            'description': costumes_dict[num]['description']
        })
    
    # 最终返回count和具体内容
    return {
        'count': len(sorted_costumes),  # 服装数量
        'costumes': sorted_costumes     # 具体服装列表
    }

# 测试示例
if __name__ == "__main__":
    # 模拟测试内容
    test_content = """0:costume_description1
博丽灵梦的日常穿着。\n红白巫女服配上大大的红缎带。
0:costume_description2
八云紫参考外界的资料，\n为灵梦准备的制服。
0:costume_name1
博丽神社的巫女小姐
0:costume_name2
悠然自得的班长"""
    
    result = parse_cos_file(test_content)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
