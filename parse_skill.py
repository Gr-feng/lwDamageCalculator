import re

def parse_skill_file(content):
    """解析主动技能文件（skill类型），适配真实格式：每行是key（如1:a），下一行是value"""
    lines = content.strip().split('\n')
    skills_data = {}
    current_key = None  # 记录当前待赋值的技能属性键（如1:a）
    
    for line in lines:
        line = line.strip()
        # 跳过空行
        if not line:
            continue
        
        # 判断当前行是「技能属性键」（如1:a）还是「属性值」（如1,2,2,2,2）
        if re.match(r'^\d+:\w+$', line):
            # 这一行是技能属性键（如1:a），记录下来，等待下一行赋值
            current_key = line
        elif current_key is not None:
            # 这一行是属性值，给上一个记录的current_key赋值
            # 解析current_key中的技能编号和属性
            match = re.match(r'^(\d+):(\w+)$', current_key)
            if match:
                skill_id, prop = match.groups()
                # 初始化技能字典
                if skill_id not in skills_data:
                    skills_data[skill_id] = {
                        'a': [], 'b': [], 'c': [],
                        'cd': 0, 'name': ''
                    }
                
                # 根据属性类型解析值
                value = line
                if prop in ['a', 'b', 'c']:
                    # a/b/c是数字列表
                    try:
                        skills_data[skill_id][prop] = list(map(int, value.split(',')))
                    except ValueError:
                        skills_data[skill_id][prop] = value.split(',') if value else []
                elif prop == 'cd':
                    # cd是整数
                    try:
                        skills_data[skill_id]['cd'] = int(value) if value else 0
                    except ValueError:
                        skills_data[skill_id]['cd'] = value if value else 0
                elif prop == 'name':
                    # name是字符串
                    skills_data[skill_id]['name'] = value
            
            # 赋值完成后清空current_key，准备下一个键值对
            current_key = None
    
    # 转换为有序列表
    sorted_skills = []
    for skill_id in sorted(skills_data.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        skill_info = skills_data[skill_id].copy()
        skill_info['id'] = int(skill_id) if skill_id.isdigit() else 0
        sorted_skills.append(skill_info)
    
    return {
        'count': len(sorted_skills),
        'skills': sorted_skills
    }

# 测试示例（完全匹配你的文件格式）
if __name__ == "__main__":
    # 完全复刻你的技能文件内容
    test_content = """1:a
1,2,2,2,2
1:b
1,12,1,3,4
1:c

1:cd
4
1:name
成就心愿的祈祷
2:a
1,7,2,2,3
2:b
1,4,2,2,2
2:c

2:cd
4
2:name
灵梦的驱魔棒
3:a
4,0,1,1,2
3:b
13,2,2,3,30
3:c
1,2,1,3,3
3:cd
5
3:name
博丽的御守"""
    
    result = parse_skill_file(test_content)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
