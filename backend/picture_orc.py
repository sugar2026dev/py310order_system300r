# backend/picture_orc.py
# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request
import requests
import base64
import json
import re
import os
import time
import uuid
import logging
from PIL import Image
import config  # 导入配置文件

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 全局变量缓存 Access Token
BAIDU_ACCESS_TOKEN = None
TOKEN_EXPIRES_AT = 0

# 必需的字段顺序 (与前端约定)
REQUIRED_FIELDS = [
    '订单编号', '商品名称', '商品规格', '商品价格', '实付金额',
    '支付方式', '物流公司', '快递单号', '订单状态', '收件人',
    '联系方式', '收货地址', '店铺名称', '下单时间', '拼单时间', '发货时间'
]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

#  百度 API 工具函数 

def get_access_token():
    """获取百度 Access Token (带缓存机制)"""
    global BAIDU_ACCESS_TOKEN, TOKEN_EXPIRES_AT
    
    current_time = time.time()
    if BAIDU_ACCESS_TOKEN and current_time < TOKEN_EXPIRES_AT:
        return BAIDU_ACCESS_TOKEN

    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": config.BAIDU_API_KEY,
        "client_secret": config.BAIDU_SECRET_KEY
    }
    
    print("🔄 [Baidu] 正在刷新 Access Token...")
    try:
        response = requests.post(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            BAIDU_ACCESS_TOKEN = data.get("access_token")
            # 提前 1 天过期，确保安全
            TOKEN_EXPIRES_AT = current_time + data.get("expires_in", 2592000) - 86400
            print("✅ [Baidu] Token 获取成功")
            return BAIDU_ACCESS_TOKEN
        else:
            print(f"❌ [Baidu] Token 获取失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ [Baidu] Token 请求异常: {e}")
        return None

def get_baidu_ocr_result(image_path):
    """调用百度高精度 OCR"""
    token = get_access_token()
    if not token:
        return {"error_msg": "无法获取 Access Token"}

    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    
    try:
        # 读取并压缩图片 (如果需要)
        # 百度限制 base64 后 4MB，这里做一个简单的检查
        with open(image_path, 'rb') as fp:
            image_data = fp.read()
            
        # 如果图片过大，可以考虑在这里用 PIL resize，目前暂略
        
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'image': image_base64,
            'access_token': token,
            'detect_direction': 'false', # 不检测朝向，减少耗时
            'probability': 'false'
        }
        
        print("☁️ [Baidu] 发送 OCR 请求...")
        response = requests.post(url, headers=headers, data=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ [Baidu] OCR 请求异常: {e}")
        return {"error_msg": str(e)}

#  核心解析逻辑 (移植自 04_batch_ocr_optimized.py) 

def is_time_str(s):
    """判断字符串是否像时间 (HH:MM:SS)"""
    return re.match(r'^\d{2}:\d{2}:\d{2}$', s.strip()) is not None

def clean_ocr_text(text):
    """清理OCR带来的常见杂质"""
    if not text: return ""
    text = re.sub(r'展开[√>]*$', '', text)
    text = text.replace('展开√', '').strip()
    return text
def parse_pdd_advanced(lines):
    """
    高级解析逻辑：针对拼多多截图优化
    """
    data = {k: None for k in REQUIRED_FIELDS}
    
    shop_line_idx = -1
    price_line_idx = -1
    
    # === 第一轮扫描 ===
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 1. 订单状态
        if i < 6 and not data['订单状态']:
            if any(s in line for s in ['待取件', '已签收', '运输中', '交易成功', '待发货', '退款成功']):
                data['订单状态'] = line
        
        # 2. 店铺名称
        if not data['店铺名称'] and '>' in line:
            if '店' in line or '旗舰' in line or '商贸' in line:
                if len(line) > 4 and '查看' not in line:
                    data['店铺名称'] = line.split('>')[0].strip()
                    shop_line_idx = i

        # 3. 价格定位
        if price_line_idx == -1 and ('￥' in line or '¥' in line):
            if '实付' not in line and '优惠' not in line:
                if re.search(r'[￥¥]\s*\d+\.?\d*', line):
                    price_line_idx = i
                    m = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
                    if m: data['商品价格'] = m.group(1)

        # 4. 联系方式、姓名、地址
        if not data['联系方式']:
            phone_match = re.search(r'(1[3-9]\d[\d\*]{6,8}\d{2,4})', line)
            if phone_match:
                phone_raw = phone_match.group(1)
                data['联系方式'] = phone_raw
                
                parts = line.split(phone_raw)
                left_part = parts[0].strip()
                if left_part:
                    name = re.sub(r'[^\u4e00-\u9fff]', '', left_part)
                    if name and name not in ['收货人']:
                        data['收件人'] = name
                
                right_part = parts[1].strip() if len(parts) > 1 else ""
                right_part = re.sub(r'号码保护中.*', '', right_part)
                right_part = re.sub(r'm\d*', '', right_part)
                
                if len(right_part) > 3:
                    data['收货地址'] = clean_ocr_text(right_part)
                elif i + 1 < len(lines):
                    next_line = clean_ocr_text(lines[i+1])
                    if any(k in next_line for k in ['省', '市', '区', '路', '街', '号', '室', '大院']):
                        data['收货地址'] = next_line

        # 5. 实付金额
        if '实付' in line:
            m = re.search(r'[￥¥]\s*(\d+\.?\d*)', line)
            if m:
                data['实付金额'] = m.group(1)
            elif '0' in line or 'O' in line:
                 data['实付金额'] = '0'

        # 6. 单号提取
        if '订单编号' in line:
            data['订单编号'] = re.sub(r'[^\d-]', '', line)
        if '快递单号' in line:
            raw = line.split('单号')[-1]
            data['快递单号'] = re.sub(r'[^\w]', '', raw)
        if '物流公司' in line:
            comp = line.split('司')[-1].replace('：', '').replace(':', '').strip()
            data['物流公司'] = comp
        if '支付方式' in line:
             data['支付方式'] = line.split('式')[-1].replace('：', '').replace(':', '').strip()

        # 7. 时间提取
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            date_str = date_match.group(1)
            time_part = ""
            
            curr_time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
            if curr_time_match:
                time_part = curr_time_match.group(1)
            elif i + 1 < len(lines) and is_time_str(lines[i+1]):
                time_part = lines[i+1].strip()
            
            if time_part:
                full_time = f"{date_str} {time_part}"
                if '下单' in line: data['下单时间'] = full_time
                elif '拼单' in line: data['拼单时间'] = full_time
                elif '发货' in line: data['发货时间'] = full_time
                elif '成交' in line and not data['发货时间']: data['发货时间'] = full_time

    # === 第二轮：商品名称推断 ===
    if not data['商品名称'] and shop_line_idx != -1 and price_line_idx != -1:
        if price_line_idx > shop_line_idx:
            candidates = lines[shop_line_idx+1 : price_line_idx]
            valid_candidates = []
            specs = []
            for c in candidates:
                c = c.strip()
                if len(c) < 2 or c in ['品牌', '好货', '百亿补贴', '退货包运费', '11.11']: continue
                if '×' in c or '*' in c or '【' in c or 'ml' in c.lower():
                    specs.append(c)
                else:
                    valid_candidates.append(c)
            
            if valid_candidates:
                data['商品名称'] = sorted(valid_candidates, key=len, reverse=True)[0]
            elif candidates:
                data['商品名称'] = candidates[0]
            
            if specs:
                data['商品规格'] = ' '.join(specs)

    # === 第三轮：兜底处理 ===
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

    # === [关键修改] 格式化输出 ===
    final_result = {}
    for k in REQUIRED_FIELDS:
        val = data.get(k)
        if val and str(val).strip():
            final_result[k] = str(val).strip()
        else:
            # 针对不同字段类型做不同处理
            if '时间' in k:
                # 时间字段如果填中文，前端日期控件可能会挂，建议留空
                final_result[k] = "" 
            elif k in ['商品价格', '实付金额']:
                # 金额建议留空
                final_result[k] = ""
            else:
                # 文本字段填入 "[未识别到...]"
                final_result[k] = f"[未识别到{k}]"
        
    return final_result

    
#  Flask 接口 

@app.route('/pic', methods=['POST'])
def pic():
    """接收图片 -> 百度OCR -> 解析 -> 返回JSON"""
    temp_path = None
    
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '未找到图片文件'}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': '文件名为空'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': '不支持的文件格式'}), 400

        # 保存临时文件
        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
        temp_path = os.path.join(temp_dir, filename)
        file.save(temp_path)
        
        print(f"\n📸 [API] 收到图片: {filename}, 大小: {os.path.getsize(temp_path)} bytes")

        # 1. 调用百度 OCR
        baidu_res = get_baidu_ocr_result(temp_path)
        
        if 'words_result' not in baidu_res:
            error_msg = baidu_res.get('error_msg', 'OCR API 未知错误')
            print(f"❌ [API] 识别失败: {error_msg}")
            return jsonify({'success': False, 'error': f"百度OCR失败: {error_msg}"}), 500

        # 2. 提取文本行
        raw_lines = [w['words'] for w in baidu_res['words_result']]
        print(f"📝 [API] OCR 提取到 {len(raw_lines)} 行文本")
        
        # 3. 智能解析
        extracted_data = parse_pdd_advanced(raw_lines)
        
        # 计算提取数量用于日志
        filled_count = sum(1 for v in extracted_data.values() if v)
        print(f"✅ [API] 解析成功，提取字段: {filled_count}/{len(REQUIRED_FIELDS)}")
        print(json.dumps(extracted_data, indent=2, ensure_ascii=False))

        # 4. 构造返回 (保持原有接口结构，方便前端兼容)
        response_data = {
            'success': True,
            'data': extracted_data,
            'message': 'OCR识别成功',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(response_data)

    except Exception as e:
        print(f"❌ [API] 系统异常: {str(e)}")
        logger.error(e, exc_info=True)
        return jsonify({'success': False, 'error': f"服务器内部错误: {str(e)}"}), 500
        
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"🧹 [API] 清理临时文件: {temp_path}")
            except:
                pass

@app.route('/')
def index():
    return '<h1>拼多多订单 OCR 服务 (Baidu API Ver)</h1>'

if __name__ == '__main__':
    # 注意：生产环境建议使用 Gunicorn
    app.run(debug=True, host='0.0.0.0', port=5000)