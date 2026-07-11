import re

def parse_unit_file(content):
    """
    解析unit类型文件（芙兰朵露·斯卡雷特这类角色基础属性）
    特征：所有键以0:开头，值包含字符串、整数、列表等类型
    返回结构化的角色基础属性字典
    新增：忽略所有以line和rank_up开头的键
    """
    lines = content.strip().split('\n')
    unit_data = {}
    current_key = None  # 记录当前待赋值的键（如0:name）
    
    # 定义需要忽略的键前缀
    IGNORE_PREFIXES = ['line', 'rank_up','voice','vocal','ability']
    
    for line in lines:
        # 预处理：移除首尾空白，跳过纯空行
        line = line.strip()
        if not line:
            continue
        
        # 判断当前行是「键行」（如0:name）还是「值行」
        if re.match(r'^0:\w+(_\d+)?$', line):
            # 这一行是键行，先检查是否需要忽略
            key_without_prefix = line.replace('0:', '')
            # 检查键是否以需要忽略的前缀开头
            if any(key_without_prefix.startswith(prefix) for prefix in IGNORE_PREFIXES):
                current_key = None  # 标记为忽略，后续值行也会被跳过
            else:
                current_key = line  # 正常记录键
        elif current_key is not None:
            # 这一行是值行，给上一个记录的键赋值（已过滤忽略的键）
            key = current_key.replace('0:', '')
            value = line
            
            # 根据值的类型解析
            parsed_value = None
            if ',' in value:
                # 列表类型（如tribe: 5,17,4...）
                value_items = [v.strip() for v in value.split(',') if v.strip()]
                try:
                    parsed_value = list(map(int, value_items))
                except ValueError:
                    # 转换失败则保留字符串列表
                    parsed_value = value_items
            else:
                # 单个值类型（区分整数、浮点数、字符串）
                if value.isdigit():
                    parsed_value = int(value)
                elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
                    parsed_value = float(value)
                else:
                    # 字符串类型（如name、ability_name等）
                    parsed_value = value
            
            # 存入数据字典
            unit_data[key] = parsed_value
            unit_data['re'] = "False" #默认角色为未转生
            # 清空当前键，准备下一个键值对
            current_key = None
    
    # 结构化返回结果（补充基础信息）
    result = {
        'character_info': unit_data,  # 角色基础属性
        'attribute_count': len(unit_data)  # 属性字段数量
    }
    
    return result

# 测试示例
if __name__ == "__main__":
    # 代入你提供的完整unit文件内容
    test_content = """0:ability_description
陶醉于常秋世界的爱丽丝·玛格特罗伊德的能力(东方归言录原创)。\n能力和通常世界的爱丽丝没有区别。\n由于这个爱丽丝是常夏世界的居民，因此对自己的兴趣爱好很诚实。\n爱丽丝的目标是宣传人偶的美好之处。\n\n常秋幻想乡中规模最大的同人即卖会。\n除此之外博丽神社、守矢神社、红魔馆、地灵殿、冥界的白玉楼等地也会定期举办即卖会。\n然而永远亭主办的新·月都万象展，无论是作品类型数还是周边数还是参加社团数都比其他即卖会要高出一个档次。\n讴歌艺术之秋爱好之秋的人们，纷纷在即卖会中展现出了自己的爱。\n亲手制作作品并与同好们分享……这份快乐不知为何会令人联想到弹幕游戏。\n爱丽丝作为人偶师……作为手办原型师见证了即卖会文化的历史。\n同时，她依然在与死线搏斗（就像历代的同人创作者们一样）。\n她现在可没有多少时间回顾历史。\n\n秋天迟迟不结束的神秘异世界。\n世界的诞生原因还在调查中。\n秋天在气质意义上是成果与衰退的季节。\n农作物的收获建立在农民数不清的汗水之上，我们无法只收获不付出（无论这是多么充满魅力的结果）。\n衰退的事物终有一日会触底反弹，这个世界上不存在永久的衰退。\n常秋明显是不自然的，照理说无法成立的现象。\n讴歌艺术和爱好是丰收象征的同时，或许也是衰退带来的惨叫声。\n\n爱丽丝一边与数不清的死线搏斗，一边思考着这些问题。\n自己说不定发现了世界的秘密。\n但这个世界没有人闲到有时间调查这种问题。\n“对了……我把魔理沙给忘了”
0:ability_effect_d1

0:ability_effect_d2
对有利属性<color=#CCAA00>造成的伤害</color><color=#FF6600>上升</color>30%
0:ability_effect_d3
免疫结界异常「<color=#CCAA00>燃烧</color>」「<color=#CCAA00>冻结</color>」「<color=#CCAA00>感电</color>」「<color=#CCAA00>黑暗</color>」且<color=#CCAA00>灵力</color><color=#00CC66>上升</color>0.20
0:ability_effect_d4
使用灵力强化时，己方全体<color=#CCAA00>阴防</color><color=#FF6600>上升</color>1等级 (1回合)
0:ability_effect_d5
使用擦弹时，己方全体<color=#CCAA00>会心命中</color><color=#FF6600>上升</color>1等级 (1回合)
0:ability_name
「操控人偶程度的能力(天)」
0:advantage_attack
30
0:advantage_resist
0
0:barrier_status_1
5
0:barrier_status_2
5
0:barrier_status_3
5
0:barrier_status_4
0
0:barrier_status_5
5
0:bgm
秋空模様
0:boost_buff
4
0:boost_target
1
0:break_cost
503
0:chain_character
11044
0:chain_description
作为后卫时，换位对象<color=#CCAA00>阳防、阴防、会心防御、会心回避</color><color=#FF6600>上升</color>(3回合)\n作为前卫时，<color=#FF6600>继承</color>换位对象<color=#CCAA00>阳防、阴防、会心防御、会心回避</color>强度上升的一部分(3回合)
0:chain_name
防御连携
0:costume_description1
陶醉于常秋世界的爱丽丝的常服。\n魔像使与造形神……劲敌太多了！
0:costume_name1
七色手办原型师
0:disadvantage_attack
0
0:disadvantage_resist
0
0:genic_name

0:get
我是天才美少女造型师爱丽丝·玛格特罗伊德。文，你不准拍我！ 我不是在cos！我平时就穿这身衣服！
0:graze_buff
10
0:graze_target
1
0:hp
5750
0:jp_name
ありす·ま—がとろいど
0:lines1
削掉这里……这里再来点……好！ 『超上海-新月万1版本-』……彩色原型完成！ 我果然是天才。我以后就自称美少女天才造形师爱丽丝·玛格特罗伊德吧。我得放进盒子里，不能把它弄坏了……什么！？ 这里是博丽神社吗！？ 为什么？ 什么情况！？ 不是吧……马上就到死线了好不好—！？
0:lines10
不能小看造形师成美。明明是用石头做的哥雷姆手办，皮肤却温暖而又柔软，关节光滑到看不出分界线！
0:rank_up_lv0_1_name
伽罗
0:rank_up_lv0_1_value
20
0:name
爱丽丝·玛格特罗伊德
0:passivity_1_description
被攻击时，受到来自<color=#CCAA00>秋季有缘者</color>的伤害<color=#0066FF>下降</color>45% [发生率100%]
0:passivity_1_icon
characteristic_icon_56
0:passivity_1_name
超上海DX装备
0:quality
11211120
0:quality_description
陶醉于常秋世界的爱丽丝·玛格特罗伊德的气质(东方归言录原创)。\n“初霰”指冬天第一场霰（即是离秋天最近的时期下的冬霰）。\n是符合常秋世界的手办原型师爱丽丝的气质。\n\n三精五行的法则已彻底被重构。\n人偶是用源自土的成分做的（强于土行），制作过程中也会用火烤（强于火行）。\n但不能随便碰。（弱于星精）
0:quality_name
初霰
0:short_name
爱丽丝
0:speed
1500
0:subname
七色手办原型师
0:total
7800
0:tribe
3,5,34,36,55,52,25,56,60,97,205,95
0:type
3
0:vocal1
中林新夏
0:vocal2
生田輝
0:vocal3
大橋彩香
0:voice1
手办造型师程度的声音
0:voice2
七色手办程度的声音
0:voice3
七色创作者程度的声音
0:world_group
C3<
0:world_group_description
“C系列的世界团（C世界团）”中的世界群之一。\n“C5世界群”在“C世界团”中偏差度是“3”左右，是例外因素稍微有点多的世界群。\n“C”是“Colloquialism”，是意味着“口语”的符号。\n日语中的接尾词“<”意味着朝特定方向发生变化，在这个世界群中的含义是“气质从夏变成秋”。\n\n【主要的分岐点】\nC世界团的世界照理说到处都是水。\n在通常的C世界团，世界的几乎所有气质都会化作“大海”。但是在这个世界群中水返祖成了金，所以一切气质集中于果实、成果、作品。\n因此在这个世界群，“成果之秋”拥有异常性的力量。\n\n【主要的汇合点】\n由于“成果之秋”支配着世界，拥有意志的存在会不断重复“文化与技艺”的仪式。\n这恐怕是这个世界弥漫着即卖会气息的原因。
0:world_group_name
C3<世界群
0:yang_atk
750
0:yang_def
1250
0:yin_atk
1650
0:yin_def
1500"""
    
    # 解析并打印结果
    unit_result = parse_unit_file(test_content)
    import json
    # 解决中文和特殊符号的序列化问题
    print(json.dumps(unit_result, ensure_ascii=False, indent=2))
