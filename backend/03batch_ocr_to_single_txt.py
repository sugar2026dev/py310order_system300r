# -*- coding: utf-8 -*-
import base64
import requests
import json
import re
import os
import time

# ================= 配置区域 =================
# 百度 API 配置
API_KEY = "uvgL3QE0cyIDG5qowfnOR4JS"
SECRET_KEY = "BwP1QfCKrbFfSki7uqiaFh4EItu0ONHZ"

# 图片输入目录
INPUT_DIR = r"C:\02media\01sharefile\01order_info\0126\300\py310order_system300r\pic"

# 结果输出文件
OUTPUT_FILE = os.path.join(INPUT_DIR, "ocr_result_optimized.txt")

# 严格要求的字段顺序
REQUIRED_FIELDS = [
    '订单编号',
    '商品名称',
    '商品规格',
    '商品价格',
    '实付金额',
    '支付方式',
    '物流公司',
    '快递单号',
    '订单状态',
    '收件人',
    '联系方式',
    '收货地址',
    '店铺名称',
    '下单时间',
    '拼单时间',
    '发货时间'
]
# ===========================================

def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as e:
        print(f"❌ 获取 Token 异常: {e}")
    return None

def get_baidu_ocr_result(image_path, token):
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    try:
        with open(image_path, 'rb') as fp:
            image_data = fp.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'image': image_base64, 'access_token': token}
        
        response = requests.post(url, headers=headers, data=data)
        return response.json()
    except Exception as e:
        return {"error_msg": str(e)}

def is_time_str(s):
    """判断字符串是否像时间 (HH:MM:SS)"""
    return re.match(r'^\d{2}:\d{2}:\d{2}$', s.strip()) is not None

def clean_ocr_text(text):
    """清理OCR带来的常见杂质"""
    if not text: return ""
    # 去除末尾的展开符号
    text = re.sub(r'展开[√>]*$', '', text)
    text = text.replace('展开√', '').strip()
    return text

def parse_pdd_advanced(lines):
    """
    高级解析逻辑：针对拼多多截图优化
    """
    # 初始化所有字段为 None，方便后续判断
    data = {k: None for k in REQUIRED_FIELDS}
    
    # 辅助索引
    shop_line_idx = -1
    price_line_idx = -1
    
    # === 第一轮扫描：定位关键行和基础信息 ===
    for i, line in enumerate(lines):
        line = line.strip()
        clean_line = clean_ocr_text(line)
        
        # 1. 订单状态 (通常在前5行)
        if i < 6 and not data['订单状态']:
            if line in ['待取件', '已签收', '运输中', '交易成功', '待发货', '待付款', '已发货，退款成功']:
                data['订单状态'] = line
        
        # 2. 店铺名称 (通常包含 > 且在商品上方)
        # 排除 "查看>" "品牌好货>" 等短词
        if not data['店铺名称'] and '>' in line:
            if '店' in line or '旗舰' in line or '商贸' in line:
                if len(line) > 4 and '查看' not in line:
                    data['店铺名称'] = line.split('>')[0].strip()
                    shop_line_idx = i

        # 3. 价格定位 (找到第一个出现的类似价格的行，通常是商品单价)
        # 排除 "实付" 行，那个在下面
        if price_line_idx == -1 and ('￥' in line or '¥' in line):
            if '实付' not in line and '优惠' not in line:
                # 确保是纯价格或简单价格行
                if re.search(r'[￥¥]\s*\d+\.?\d*', line):
                    price_line_idx = i
                    m = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
                    if m: data['商品价格'] = m.group(1)

        # 4. 联系方式、姓名、地址 (核心难点)
        if not data['联系方式']:
            # 匹配手机号 (134****9326 或 1349326 等)
            phone_match = re.search(r'(1[3-9]\d[\d\*]{6,8}\d{2,4})', line)
            if phone_match:
                phone_raw = phone_match.group(1)
                data['联系方式'] = phone_raw
                
                # 尝试分离姓名 (在电话左边)
                left_part = line.split(phone_raw)[0].strip()
                if left_part:
                    name = re.sub(r'[^\u4e00-\u9fff]', '', left_part) # 只留中文
                    # 排除干扰词
                    if name and name not in ['收货人', '联系人']:
                        data['收件人'] = name
                
                # 尝试分离地址 (在电话右边，或者就是下一行)
                right_part = line.split(phone_raw)[1].strip()
                # 过滤掉 "号码保护中" 等
                right_part = re.sub(r'号码保护中.*', '', right_part)
                right_part = re.sub(r'm\d*', '', right_part) # 去除 OCR 误识别的 m
                
                if len(right_part) > 3: # 如果右边还有长文本，可能是地址
                    data['收货地址'] = clean_ocr_text(right_part)
                elif i + 1 < len(lines):
                    # 如果右边没东西，地址很可能在下一行
                    next_line = clean_ocr_text(lines[i+1])
                    # 简单验证下一行是不是地址
                    if any(k in next_line for k in ['省', '市', '区', '路', '街', '号', '室', '大院']):
                        data['收货地址'] = next_line

        # 5. 实付金额
        if '实付' in line:
            # 处理 "先用后付 实付: ¥0" 或 "实付: ¥35.9"
            # 优先找数字
            m = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
            if m:
                data['实付金额'] = m.group(1)
            elif '0' in line or 'O' in line: # 处理 OCR 识别 0 为 O
                 data['实付金额'] = '0'

        # 6. 单号提取
        if '订单编号' in line:
            data['订单编号'] = re.sub(r'[^\d-]', '', line)
        
        if '快递单号' in line:
            # 提取冒号后的所有字母数字
            raw_tracking = line.split('单号')[-1]
            data['快递单号'] = re.sub(r'[^\w]', '', raw_tracking)
            
        if '物流公司' in line:
            comp = line.split('司')[-1].replace('：', '').replace(':', '').strip()
            data['物流公司'] = comp

        if '支付方式' in line:
             data['支付方式'] = line.split('式')[-1].replace('：', '').replace(':', '').strip()

        # 7. 时间提取 (重点优化：多行合并)
        # 匹配日期 YYYY-MM-DD
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            date_str = date_match.group(1)
            time_part = ""
            
            # 检查当前行是否已有时间
            current_line_time = re.search(r'(\d{2}:\d{2}:\d{2})', line)
            if current_line_time:
                time_part = current_line_time.group(1)
            # 检查下一行是否是时间 (OCR 常见换行)
            elif i + 1 < len(lines) and is_time_str(lines[i+1]):
                time_part = lines[i+1].strip()
            
            full_time = f"{date_str} {time_part}".strip()
            
            if '下单' in line: data['下单时间'] = full_time
            elif '拼单' in line: data['拼单时间'] = full_time
            elif '发货' in line: data['发货时间'] = full_time
            elif '成交' in line: # 有时候发货时间显示为成交时间
                 if not data['发货时间']: data['发货时间'] = full_time

    # === 第二轮：复杂字段推断 ===
    
    # 8. 商品名称提取 (利用边界法)
    # 逻辑：在 [店铺名称行] 和 [价格行] 之间，最长的那段话通常是商品名
    if not data['商品名称'] and shop_line_idx != -1 and price_line_idx != -1:
        if price_line_idx > shop_line_idx:
            candidates = lines[shop_line_idx+1 : price_line_idx]
            
            # 过滤干扰行
            valid_candidates = []
            specs_candidates = []
            
            for c in candidates:
                c = c.strip()
                if len(c) < 2: continue
                if c in ['品牌', '好货', '百亿补贴', '退货包运费', '11.11', '特惠装']: continue
                if '>' in c and len(c) < 5: continue
                
                # 识别规格行 (包含 x1, *1, 【】)
                if '×' in c or '*' in c or '【' in c or '】' in c or 'ml' in c.lower() or 'g' in c.lower():
                    specs_candidates.append(c)
                else:
                    valid_candidates.append(c)
            
            # 从剩下的候选里，选最长的作为商品名
            if valid_candidates:
                # 排序取最长
                data['商品名称'] = sorted(valid_candidates, key=len, reverse=True)[0]
            elif len(candidates) > 0:
                # 实在没得选，取第一行
                data['商品名称'] = candidates[0]

            # 9. 商品规格
            if specs_candidates:
                data['商品规格'] = ' '.join(specs_candidates)

    # === 第三轮：兜底处理 ===
    # 如果没找到物流公司，但有单号，尝试推断
    if not data['物流公司'] and data['快递单号']:
        tn = data['快递单号']
        if tn.startswith('YT') or tn.startswith('88'): data['物流公司'] = '圆通快递'
        elif tn.startswith('SF'): data['物流公司'] = '顺丰速运'
        elif tn.startswith('JT'): data['物流公司'] = '极兔速递'
        elif tn.startswith('77'): data['物流公司'] = '申通快递'
        elif tn.startswith('75') or tn.startswith('78'): data['物流公司'] = '中通快递'
        elif tn.startswith('98'): data['物流公司'] = '邮政快递'
        elif tn.startswith('46'): data['物流公司'] = '韵达快递'
        elif tn.startswith('JYM'): data['物流公司'] = '加运美'

    # 将 None 转为 "(未识别)" 或用户要求的格式
    final_result = {}
    for k in REQUIRED_FIELDS:
        val = data.get(k)
        if val:
            final_result[k] = str(val).strip()
        else:
            final_result[k] = "(未识别)"
            
    return final_result

def main():
    print(f"🚀 开始优化版批量识别...")
    print(f"📄 结果将写入: {OUTPUT_FILE}")
    
    token = get_access_token()
    if not token:
        print("❌ Token 获取失败")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    files.sort() # 按文件名排序，方便查看
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        f_out.write(f"百度 OCR 优化版识别报告\n")
        f_out.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write("=" * 60 + "\n\n")

        for idx, filename in enumerate(files):
            file_path = os.path.join(INPUT_DIR, filename)
            print(f"[{idx+1}/{len(files)}] 处理: {filename} ...")
            
            # 1. OCR
            raw_json = get_baidu_ocr_result(file_path, token)
            
            f_out.write(f"############################################################\n")
            f_out.write(f"FILE: {filename}\n")
            f_out.write(f"############################################################\n\n")
            
            if 'words_result' in raw_json:
                raw_lines = [w['words'] for w in raw_json['words_result']]
                
                # 2. 调用高级解析逻辑
                parsed_data = parse_pdd_advanced(raw_lines)
                
                # 3. 写入字段 (按顺序)
                f_out.write("--- [解析结果] ---\n")
                for field in REQUIRED_FIELDS:
                    value = parsed_data.get(field, "(未识别)")
                    f_out.write(f"{field:<8}: {value}\n")
                
                # 4. 写入原始文本 (用于调试)
                f_out.write("\n--- [OCR 原始文本] ---\n")
                for i, line in enumerate(raw_lines):
                    f_out.write(f"{i+1:02d}: {line}\n")
                    
            else:
                f_out.write(f"❌ 识别失败: {json.dumps(raw_json, ensure_ascii=False)}\n")
            
            f_out.write("\n\n")
            f_out.flush()
            time.sleep(0.3)

    print(f"\n✨ 全部完成！请查看: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()