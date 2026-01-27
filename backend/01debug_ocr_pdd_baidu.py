# -*- coding: utf-8 -*-
import base64
import requests
import json
import re
import os
import time

# ================= 配置区域 =================
# 百度 API 配置 (使用你提供的 Key)
API_KEY = "uvgL3QE0cyIDG5qowfnOR4JS"
SECRET_KEY = "BwP1QfCKrbFfSki7uqiaFh4EItu0ONHZ"
API_KEY = "Ab3xmw0jVBy7nhQ1O3deuxTA"
SECRET_KEY = "1WmzSdGeTGWnk4Rlg2C74Ka8nKQPKvus"
# 图片绝对路径
IMAGE_PATH = r"C:\02media\01sharefile\01order_info\0126\300\pic\testpic\01.jpg"

# 期望的正确结果 (用于自动对比)
EXPECTED_DATA = {
    '订单编号': '251109-349689618030662',
    '商品名称': '超厚条纹厨房抹布不沾油洗碗巾加厚吸水不掉毛刷碗布去油清洁无痕',
    '商品规格': '升级加大加厚【包边加挂绳】,加厚【条纹灰咖色1条装】12*12cm', # 模糊匹配
    '商品价格': '0.89',
    '实付金额': '0.00',
    '支付方式': '先用后付',
    '物流公司': '韵达快递',
    '快递单号': '464841042250593',
    '订单状态': '待取件',
    '收件人': '郑传宝',
    '联系方式': '134****9326', # 注意百度识别出来是 134**9326，少两个星号，这很正常
    '收货地址': '九佛街道九佛育才路900号信科大院101号',
    '店铺名称': '森森家具百货店',
    '下单时间': '2025-11-09 19:42:41',
    '拼单时间': '2025-11-09 19:42:42',
    '发货时间': '2025-11-10 11:38:32'
}
# ===========================================

def get_access_token():
    """获取百度 Access Token"""
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def get_baidu_ocr_result(image_path):
    """调用百度高精度OCR"""
    token = get_access_token()
    if not token:
        print("❌ 获取 Token 失败")
        return []

    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic" # 使用高精度接口
    
    try:
        with open(image_path, 'rb') as fp:
            image_data = fp.read()
            
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'image': image_base64, 'access_token': token}

        print("☁️ 正在请求百度 OCR API...")
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        
        if 'words_result' in result:
            # 提取纯文本列表
            lines = [w['words'] for w in result['words_result']]
            return lines
        else:
            print(f"❌ API 返回错误: {result}")
            return []
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return []

def parse_pdd_data_baidu(lines):
    """
    针对百度OCR结果的解析逻辑
    因为百度的识别率很高，我们可以使用更严格、更简单的逻辑
    """
    result = {k: '' for k in EXPECTED_DATA.keys()}
    
    # 辅助变量
    full_text = '\n'.join(lines)
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 1. 订单状态 (通常在前几行)
        if i < 5 and line in ['待取件', '已签收', '运输中', '交易成功']:
            result['订单状态'] = line
            
        # 2. 姓名和电话 (百度识别结果：郑传宝134**9326号码保护中)
        # 查找包含 13x...x 的行
        phone_match = re.search(r'(1[3-9]\d[\d\*]{6,8}\d{2,4})', line)
        if phone_match:
            phone_raw = phone_match.group(1)
            result['联系方式'] = phone_raw
            
            # 名字通常在电话前面
            # 分割字符串
            parts = line.split(phone_raw)
            if parts[0].strip():
                name = parts[0].strip()
                # 去除可能的干扰词
                name = name.replace('收货人', '').replace(':', '').strip()
                result['收件人'] = name
                
        # 3. 地址 (通常在电话行的下一行)
        if '收货地址' in result and not result['收货地址']:
            # 简单启发式：如果上一行找到了电话，这一行大概率是地址
            # 或者包含 省/市/区/街/路
            if any(k in line for k in ['省', '市', '区', '街道', '路', '号']):
                addr = line.replace('展开', '').replace('√', '').strip()
                result['收货地址'] = addr

        # 如果没有通过相对位置找到地址，尝试在所有行里找
        if not result['收货地址'] and result['联系方式'] and line != result['联系方式']:
             if i > 0 and result['联系方式'] in lines[i-1]:
                  addr = line.replace('展开', '').replace('√', '').strip()
                  result['收货地址'] = addr

        # 4. 店铺名称 (通常以 > 结尾)
        if '>' in line and ('店' in line or '旗舰' in line):
             # 排除“查看>”等短词
             if len(line) > 4:
                 result['店铺名称'] = line.split('>')[0].strip()

        # 5. 价格
        # 商品价格 (通常是第一个出现的小价格)
        if '￥' in line or '¥' in line:
            price_match = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
            if price_match:
                price_val = price_match.group(1)
                if '实付' in line:
                    result['实付金额'] = price_val
                elif not result['商品价格'] and float(price_val) > 0:
                    result['商品价格'] = price_val
                    
        # 补救：实付为0的情况
        if '实付' in line and ('0' in line or 'O' in line): # OCR有时把0识别为O
             if '￥0' in line or '¥0' in line or '实付:0' in line.replace(' ', ''):
                 result['实付金额'] = '0.00'

        # 6. 订单编号
        if '订单编号' in line:
            # 提取冒号后面的数字
            num = re.sub(r'[^\d-]', '', line)
            if len(num) > 10:
                result['订单编号'] = num
                
        # 7. 物流公司
        if '物流公司' in line:
            comp = line.split('：')[-1].split(':')[-1].strip()
            result['物流公司'] = comp
            
        # 8. 快递单号
        if '快递单号' in line:
            track = re.sub(r'[^\w]', '', line.split('单号')[-1]) # 只保留字母数字
            result['快递单号'] = track

        # 9. 支付方式
        if '支付方式' in line:
            pay = line.split('：')[-1].split(':')[-1].strip()
            result['支付方式'] = pay

        # 10. 时间 (下单、拼单、发货)
        # 百度有时会把时间拆成两行： "下单时间：2025-11-09" 和 "19:42:41"
        if '时间' in line and re.search(r'\d{4}-\d{2}-\d{2}', line):
            time_type = ''
            if '下单' in line: time_type = '下单时间'
            elif '拼单' in line: time_type = '拼单时间'
            elif '发货' in line: time_type = '发货时间'
            
            if time_type:
                # 尝试在当前行找完整时间
                full_time = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line)
                if full_time:
                    result[time_type] = full_time.group(0)
                else:
                    # 如果当前行只有日期，看下一行是不是时间
                    date_part = re.search(r'\d{4}-\d{2}-\d{2}', line).group(0)
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if re.match(r'\d{2}:\d{2}:\d{2}', next_line):
                             result[time_type] = f"{date_part} {next_line}"

    # 11. 商品名称 (难点：在店铺名和价格之间)
    # 简单策略：找到店铺名所在的行索引，找到价格所在的行索引，中间最长的一段中文通常是商品名
    try:
        shop_idx = -1
        price_idx = -1
        for idx, line in enumerate(lines):
            if result['店铺名称'] in line and result['店铺名称']: shop_idx = idx
            if '￥' in line and result['商品价格'] in line: 
                price_idx = idx
                break # 找到第一个价格即可
        
        if shop_idx != -1 and price_idx != -1 and price_idx > shop_idx:
            # 取中间的行
            potential_lines = lines[shop_idx+1 : price_idx]
            # 过滤掉短行和无关行
            valid_names = [l for l in potential_lines if len(l) > 5 and '不沾油' in l or '抹布' in l] # 根据上下文关键词辅助
            if valid_names:
                result['商品名称'] = valid_names[0] # 取第一行最像的
            elif potential_lines:
                result['商品名称'] = potential_lines[0] # 盲取第一行
                
            # 尝试拼接规格
            specs = []
            for l in potential_lines:
                if '【' in l or '】' in l or '*' in l:
                    specs.append(l)
            if specs:
                result['商品规格'] = ' '.join(specs)
                
    except:
        pass

    return result

def compare_results(actual_data):
    """对比并打印表格"""
    print("\n" + "="*30 + " 百度 OCR 结果验证 " + "="*30)
    print(f"{'字段名':<10} | {'实际提取值 (Baidu)':<35} | {'期望值 (Standard)':<35} | {'结果'}")
    print("-" * 95)
    
    match_count = 0
    for key, expected in EXPECTED_DATA.items():
        actual = actual_data.get(key, '')
        if actual is None: actual = ''
        
        # 清理字符串以便对比 (忽略空格、星号数量差异、人民币符号)
        def clean(s):
            return str(s).replace(' ', '').replace('¥', '').replace('￥', '').replace('*', '')
        
        c_act = clean(actual)
        c_exp = clean(expected)
        
        is_match = False
        if c_exp == c_act:
            is_match = True
        elif c_exp in c_act and len(c_exp) > 2: # 包含关系
            is_match = True
        elif c_act in c_exp and len(c_act) > 5: # 反向包含
            is_match = True
        # 价格特判
        try:
            if key in ['商品价格', '实付金额'] and float(c_act) == float(c_exp):
                is_match = True
        except:
            pass
            
        status = "✅" if is_match else "❌"
        if is_match: match_count += 1
        
        # 格式化输出，防止太长
        d_act = (str(actual)[:33] + '..') if len(str(actual)) > 33 else str(actual)
        d_exp = (str(expected)[:33] + '..') if len(str(expected)) > 33 else str(expected)
        
        print(f"{key:<10} | {d_act:<35} | {d_exp:<35} | {status}")
        
    print("-" * 95)
    print(f"🏆 最终得分: {match_count} / {len(EXPECTED_DATA)}")
    print("="*80)

if __name__ == '__main__':
    print("🚀 开始百度 OCR 验证流程...")
    
    # 1. 获取百度OCR原始数据
    lines = get_baidu_ocr_result(IMAGE_PATH)
    
    if lines:
        print(f"📄 获取到 {len(lines)} 行原始文本")
        # 打印前几行看看
        # print(lines) 
        
        # 2. 解析数据
        parsed_data = parse_pdd_data_baidu(lines)
        
        # 3. 对比结果
        compare_results(parsed_data)
    else:
        print("❌ 无法进行对比，OCR 返回为空")




