import re

def parse_attack_file(content):
    """
    解析attack_unit文件
    核心优化：
    1. 修复空值字段解析错误（buff/effect等空值返回[]而非错误字符串）
    2. 将effect_before_N/effect_after_N规整为列表
    3. 新增icon_before/icon_after/type_before/type_after列表解析
    4. 将damage_extend从攻击段移至全局列表
    5. 所有列表字段严格处理空值，确保空值返回[]
    """
    lines = content.strip().split('\n')
    raw_global_attrs = {}  # 原始全局属性
    attacks = {}           # 1~6开头的攻击段属性
    damage_extend_list = []# 存储各攻击段的damage_extend值
    target = []
    
    # ========== 第一步：解析原始数据（修复行索引逻辑） ==========
    # 预处理行：去除行尾逗号、空白，过滤空行
    temp_lines = []
    for l in lines:
        stripped_line = l.rstrip(',').strip()
        if stripped_line:
            temp_lines.append(stripped_line)
    
    i = 0
    while i < len(temp_lines):
        curr_line = temp_lines[i]
        # 判断是否是「键行」（格式：数字:属性名）
        if re.match(r'^\d+:\w+(_\d+)?$', curr_line):
            current_key = curr_line
            # 拆分键行
            key_parts = current_key.split(':', 1)
            if len(key_parts) != 2:
                i += 1
                continue
            
            attr_type, prop = key_parts[0].strip(), key_parts[1].strip()
            # 获取值：下一行如果是键行，则当前值为空；否则取下行作为值
            value = ''
            i += 1  # 移动到值行位置
            if i < len(temp_lines):
                next_line = temp_lines[i]
                # 检查下一行是否是键行，若是则当前值为空
                if not re.match(r'^\d+:\w+(_\d+)?$', next_line):
                    value = next_line.strip()
                    i += 1  # 是值行，继续移动索引
                # 下一行是键行，值为空，索引不移动（留给下一轮循环处理）
            
            # ========== 严格的值解析逻辑（确保空值返回[]） ==========
            parsed_value = None
            
            # 定义所有需要强制列表类型的字段
            force_list_fields = [
                'buff', 'effect', 'killers', 'break',
                'effect_before', 'effect_after', 
                'icon_before', 'icon_after',
                'type_before', 'type_after'
            ]
            
            # 判断是否为列表类型字段
            is_force_list = any(field in prop for field in force_list_fields)
            has_comma = ',' in value
            
            # 1. 列表类型字段（强制返回列表，空值返回[]）
            if is_force_list or has_comma:
                if not value:
                    parsed_value = []
                else:
                    value_items = [v.strip() for v in value.split(',') if v.strip()]
                    try:
                        parsed_value = list(map(int, value_items))
                    except (ValueError, TypeError):
                        parsed_value = value_items
            # 2. 单个值类型（兼容空值）
            else:
                if not value:
                    parsed_value = ''
                elif value.isdigit() or (value.replace('.', '', 1).isdigit() and value.count('.') <= 1):
                    try:
                        parsed_value = float(value) if '.' in value else int(value)
                    except:
                        parsed_value = value
                else:
                    parsed_value = value
            
            # ========== 分类存储数据 ==========
            if attr_type == '0':
                raw_global_attrs[prop] = parsed_value
            elif attr_type in ['1', '2', '3', '4', '5', '6']:
                if attr_type not in attacks:
                    attacks[attr_type] = {}
                # 特殊处理damage_extend：不存入攻击段，单独收集
                if prop == 'damage_extend':
                    damage_extend_list.append((int(attr_type), parsed_value))
                if prop == 'target':
                    target.append((int(attr_type), parsed_value))
                else:
                    attacks[attr_type][prop] = parsed_value
        else:
            # 非键行，跳过
            i += 1

    # ========== 第二步：规整全局列表类属性 ==========
    global_attrs = {}
    
    # 定义需要规整的列表字段配置
    list_configs = [
        ('effect_before', re.compile(r'^effect_before_(\d+)$')),
        ('effect_after', re.compile(r'^effect_after_(\d+)$')),
        ('icon_before', re.compile(r'^icon_before_(\d+)$')),
        ('icon_after', re.compile(r'^icon_after_(\d+)$')),
        ('type_before', re.compile(r'^type_before_(\d+)$')),
        ('type_after', re.compile(r'^type_after_(\d+)$'))
    ]
    
    # 1. 提取并规整所有列表类全局属性
    for list_name, pattern in list_configs:
        item_keys = []
        for key in raw_global_attrs.keys():
            match = pattern.match(key)
            if match:
                item_keys.append((int(match.group(1)), key))
        
        # 按数字升序排序并构建列表
        item_keys.sort(key=lambda x: x[0])
        item_list = [raw_global_attrs[key] for _, key in item_keys]
        
        # 即使为空也保留键（值为空列表）
        global_attrs[list_name] = item_list
    
    # 2. 处理其他全局属性（非列表类）
    for key in raw_global_attrs.keys():
        # 跳过已处理的列表类字段
        if any(pattern.match(key) for _, pattern in list_configs):
            continue
        global_attrs[key] = raw_global_attrs[key]
    
    # 3. 规整damage_extend列表（按攻击段ID排序）
    damage_extend_list.sort(key=lambda x: x[0])
    global_attrs['damage_extend'] = [v for _, v in damage_extend_list]

    # 4. 规整target列表（按攻击段ID排序）
    target.sort(key=lambda x: x[0])
    global_attrs['target'] = [v for _, v in target]

    # ========== 第三步：整理攻击段数据 ==========
    sorted_attacks = []
    for atk_id in sorted(attacks.keys(), key=lambda x: int(x)):
        attack_info = attacks[atk_id].copy()
        attack_info['attack_id'] = int(atk_id)
        sorted_attacks.append(attack_info)

    # ========== 最终返回结构化结果 ==========
    result = {
        'global_attributes': global_attrs,  # 规整后的全局属性
        'attack_count': len(sorted_attacks),# 攻击段数量
        'attacks': sorted_attacks           # 1~6段攻击信息
    }
    return result

# 测试示例
if __name__ == "__main__":
    # 代入测试内容（包含空buff/effect字段）
    test_content = """0:all_order_0
111111111111111111111111111g
0:all_order_1
12112112112112112113113113113113111111g
0:all_order_2
121121121121121121131131413151315131514114114g
0:all_order_3
12112112112112112113113141315131513151416141614g
0:description
即将抵达终局的博丽灵梦的终符(东方归言录原创)。\n通过某本魔导书回想起的弹幕。\n\n【灵梦与魔理沙】\n要想理解博丽灵梦，我们不能不提到雾雨魔理沙。\n在魔理沙眼里灵梦是懒惰的天才，同时魔理沙也自诩研究家。由此可见她们两个人做事方式是反过来的。\n她们就像是阴阳的两面一样，是相互弥补不足的存在。\n灵梦的红白是“存在和虚无”的颜色，红白境界象征“开始”。\n魔理沙的黑白是“虚构与虚无”的颜色，黑白境界象征“结束”。\n灵梦与魔理沙各自的特性都依靠着另一方的存在。正所谓阴中有阳，阳中有阴。\n虽然不知道她们两个人有没有意识到这一点。
0:effect_before_1
41,5,1,2,1
0:effect_before_2
1,8,2,5,2
0:effect_before_3
1,5,2,5,3
0:effect_before_4
2,2,4,4,2
0:effect_before_5
2,9,4,4,2
0:first_order
1
0:name
「被命名为梦想天生的弹幕」
0:power_rate
4
1:acc
95
1:amt
27
1:boost
0
1:buff

1:cri
3
1:damage
4.91
1:damage_extend
100
1:effect
1,1,5,222,
1:element
1
1:id
200025
1:killers
5,14,1,95,176
1:name
真相不明的无名弹幕
1:order

1:rate
1.0
1:target
2
1:type
8
1:yinyang
1
2:acc
90
2:amt
6
2:boost
1
2:buff
25,100,
2:cri
5
2:damage
6.10
2:damage_extend
100
2:effect

2:element
8
2:id
200026
2:killers
5,14,1,95,176
2:name
命名封印·流星
2:order

2:rate
1.0
2:target
2
2:type
9
2:yinyang
1
3:acc
90
3:amt
5
3:boost
1
3:buff

3:cri
5
3:damage
6.70
3:damage_extend
107
3:effect
1,1,5,111,
3:element
1
3:id
200027
3:killers
59,65,72,88,95,176
3:name
无意识中的自动弹幕
3:order

3:rate
1.0
3:target
2
3:type
8
3:yinyang
1
4:acc
80
4:amt
4
4:boost
2
4:buff
25,100,
4:cri
10
4:damage
8.18
4:damage_extend
114
4:effect

4:element
8
4:id
200028
4:killers
101,77,117,156,95,176
4:name
命名封印·彗星
4:order

4:rate
1.0
4:target
2
4:type
9
4:yinyang
1
5:acc
80
5:amt
3
5:boost
2
5:buff
64,100,
5:cri
10
5:damage
9.82
5:damage_extend
121
5:effect
4,111,
5:element
1
5:id
200029
5:killers
113,118,126,154,69,95,176
5:name
无法控制的暴走弹幕
5:order

5:rate
1.0
5:target
2
5:type
8
5:yinyang
1
6:acc
75
6:amt
2
6:boost
3
6:buff
25,100,
6:cri
15
6:damage
13.36
6:damage_extend
128
6:effect
5,111,12,1,
6:element
8
6:id
200030
6:killers
5,14,1,95,176
6:name
命名封印·游星
6:order

6:rate
1.0
6:target
2
6:type
9
6:yinyang
1"""
    
    # 解析并打印结果
    attack_result = parse_attack_file(test_content)
    import json
    print(json.dumps(attack_result, ensure_ascii=False, indent=2))
