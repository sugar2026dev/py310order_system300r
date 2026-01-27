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

# 结果输出文件 (保存在输入目录下)
OUTPUT_FILE = os.path.join(INPUT_DIR, "ocr_result_all.txt")
# ===========================================

def get_access_token():
    """获取百度 Access Token"""
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
    """调用百度高精度OCR"""
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

def parse_data_logic(lines):
    """
    通用的解析逻辑 (尝试提取关键信息)
    即使是空白图或不同类型的图，也会返回空字典
    """
    result = {
        '订单编号': '', '商品名称': '', '商品规格': '', '商品价格': '', '实付金额': '',
        '支付方式': '', '物流公司': '', '快递单号': '', '订单状态': '', '收件人': '',
        '联系方式': '', '收货地址': '', '店铺名称': '', '下单时间': '', '发货时间': ''
    }
    
    # 辅助变量
    full_text = '\n'.join(lines)
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 提取电话/手机 (通用匹配)
        if not result['联系方式']:
            phone_match = re.search(r'(1[3-9]\d[\d\*]{6,8}\d{2,4})', line)
            if phone_match:
                result['联系方式'] = phone_match.group(1)
                # 尝试提取同行的名字
                parts = line.split(result['联系方式'])
                if parts[0].strip():
                    name_candidate = parts[0].strip().replace('收货人', '').replace(':', '')
                    if len(name_candidate) < 10:
                        result['收件人'] = name_candidate

        # 提取地址 (通用关键词)
        if not result['收货地址']:
            if any(k in line for k in ['省', '市', '区', '街道', '路', '号', '大厦', '室']):
                if len(line) > 8: # 简单过滤短词
                    result['收货地址'] = line.replace('展开', '').replace('√', '').strip()

        # 提取金额
        if '￥' in line or '¥' in line:
            m = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
            if m:
                val = m.group(1)
                if '实付' in line: result['实付金额'] = val
                elif not result['商品价格']: result['商品价格'] = val
        
        # 提取单号 (数字+字母长串)
        if '单号' in line or '编号' in line:
            num = re.sub(r'[^\w-]', '', line.split('：')[-1].split(':')[-1])
            if len(num) > 8:
                if '订单' in line: result['订单编号'] = num
                elif '快递' in line or '运单' in line: result['快递单号'] = num
        
        # 提取时间
        if re.search(r'\d{4}-\d{2}-\d{2}', line):
            t_str = re.search(r'\d{4}-\d{2}-\d{2}', line).group(0)
            full_t = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line)
            val = full_t.group(0) if full_t else t_str
            
            if '下单' in line: result['下单时间'] = val
            elif '发货' in line: result['发货时间'] = val
            
        # 提取状态
        if line in ['待取件', '已签收', '运输中', '交易成功', '待发货', '待付款']:
            result['订单状态'] = line
            
    return result

def main():
    print(f"🚀 开始批量识别，结果将写入: {OUTPUT_FILE}")
    
    token = get_access_token()
    if not token:
        print("❌ 无法获取 Token")
        return

    # 获取所有图片文件
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.bmp'))]
    files.sort() # 按文件名排序
    
    print(f"📂 找到 {len(files)} 张图片")
    
    # 打开文件准备写入
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        f_out.write(f"百度 OCR 批量识别报告\n")
        f_out.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write("=" * 60 + "\n\n")

        for idx, filename in enumerate(files):
            file_path = os.path.join(INPUT_DIR, filename)
            print(f"[{idx+1}/{len(files)}] 正在识别: {filename} ...")
            
            # 1. 调用 OCR
            raw_json = get_baidu_ocr_result(file_path, token)
            
            # 2. 准备写入的数据块
            f_out.write(f"############################################################\n")
            f_out.write(f"FILE: {filename}\n")
            f_out.write(f"############################################################\n\n")
            
            if 'words_result' in raw_json:
                # 提取原始文本行
                raw_lines = [w['words'] for w in raw_json['words_result']]
                
                # 尝试解析
                parsed_data = parse_data_logic(raw_lines)
                
                # --- 写入解析结果 ---
                f_out.write("--- [1. 解析出的字段 (Extracted Fields)] ---\n")
                has_data = False
                for k, v in parsed_data.items():
                    if v: # 只显示有值的字段，更清晰
                        f_out.write(f"{k:<10}: {v}\n")
                        has_data = True
                if not has_data:
                    f_out.write("(未提取到有效字段)\n")
                
                # --- 写入原始文本 ---
                f_out.write("\n--- [2. 原始识别文本 (Raw OCR Text)] ---\n")
                if not raw_lines:
                    f_out.write("(空白/无文字)\n")
                for i, line in enumerate(raw_lines):
                    f_out.write(f"{i+1:02d}: {line}\n")
                
                # --- 写入原始 JSON (可选，放在最后) ---
                f_out.write("\n--- [3. API 原始 JSON 数据] ---\n")
                f_out.write(json.dumps(raw_json, ensure_ascii=False) + "\n")
                
            else:
                f_out.write("❌ 识别失败 / API 错误:\n")
                f_out.write(json.dumps(raw_json, ensure_ascii=False) + "\n")
            
            f_out.write("\n\n") # 文件间空行
            f_out.flush()     # 实时写入磁盘
            
            # 避免触发 QPS 限制
            time.sleep(0.5)

    print(f"\n✨ 全部完成！结果已保存至: {OUTPUT_FILE}")

if __name__ == '__main__':
    main()