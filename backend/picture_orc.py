# -*- coding: utf-8 -*-
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract
import re
from flask import Flask, jsonify, request
import os
import logging
import time
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

# ========== 物流公司识别配置 ==========
LOGISTICS_COMPANIES = {
    '韵达': ['韵达', 'yunda', 'YD'],
    '申通': ['申通', 'shentong', 'ST'],
    '圆通': ['圆通', 'yuantong', 'YT'],
    '中通': ['中通', 'zhongtong', 'ZT'],
    '邮政': ['邮政', '邮政快递', '快递包', 'youzheng', 'EMS'],
    '顺丰': ['顺丰', '顺丰快递', 'shunfeng', 'SF'],
    '京东': ['京东', '京东快递', 'jingdong', 'JD'],
    '百世': ['百世', '百世快递', 'baishi'],
    '天天': ['天天', '天天快递', 'tiantian'],
    '德邦': ['德邦', '德邦快递', 'debang']
}

# 根据快递单号前缀识别物流公司
TRACKING_PREFIXES = {
    '464': '韵达',
    '777': '申通',
    'YT': '圆通',
    '88': '圆通',
    '78': '中通',
    '981': '邮政',
    'SF': '顺丰',
    'JD': '京东',
    '75': '中通',
    '12': '中通',
    '10': '中通',
    '11': '申通',
}


# ========== 预处理方法 ==========
def preprocess_image(image):
    """图片预处理"""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')

        width, height = image.size
        if width > 1200:
            scale = 1000 / width
            new_width = 1000
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.2)
        image = image.filter(ImageFilter.SHARPEN)

        return image
    except Exception as e:
        logger.error(f"图片预处理失败: {e}")
        return image.convert('L') if image.mode != 'L' else image


# ========== 文本清理 ==========
def clean_ocr_text(text):
    """清理OCR文本"""
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 2:  # 第106行：这里是正确的
            continue

        # 修复常见OCR错误
        line = re.sub(r'[©™®«»"\'`~|]', '', line)
        line = re.sub(r'\s+', ' ', line).strip()

        if line:
            cleaned_lines.append(line)

    # 第583行：修复这里，使用双引号包含换行符
    return "\n".join(cleaned_lines)


# ========== 物流公司识别函数 ==========
def identify_logistics_company(line):
    """识别物流公司"""
    line_lower = line.lower()

    for company, keywords in LOGISTICS_COMPANIES.items():
        for keyword in keywords:
            if keyword.lower() in line_lower:
                return company

    return None


def identify_logistics_by_tracking(tracking_number):
    """根据快递单号识别物流公司"""
    for prefix, company in TRACKING_PREFIXES.items():
        if tracking_number.startswith(prefix):
            return company

    # 根据长度和格式推断
    if len(tracking_number) == 13 and tracking_number.isdigit():
        return '韵达'
    elif len(tracking_number) == 12 and tracking_number.isdigit():
        return '申通'
    elif tracking_number.startswith('SF') and len(tracking_number) > 10:
        return '顺丰'

    return None


# ========== 改进的布局分析 ==========
def analyze_pdd_layout(lines):
    """分析拼多多订单布局"""
    key_lines = {
        'status_line': -1,
        'phone_line': -1,
        'address_line': -1,
        'store_line': -1,
        'product_start': -1,
        'product_end': -1,
        'price_line': -1,
        'real_pay_line': -1,
        'order_start': -1,
        'buttons_line': -1,
    }

    # 0. 过滤噪音行
    valid_lines = []
    for line in lines:
        if re.match(r'^\d{1,2}:\d{2}\s+[!@#$%^&*()]', line) or '5G GE' in line:
            continue
        valid_lines.append(line)

    if not valid_lines:
        valid_lines = lines

    # 1. 状态行
    for i in range(min(5, len(valid_lines))):
        line = valid_lines[i]
        if '待取件' in line:
            key_lines['status_line'] = i
            key_lines['status_type'] = '待取件'
            break
        elif '已签收' in line:
            key_lines['status_line'] = i
            key_lines['status_type'] = '已签收'
            break
        elif '运输中' in line:
            key_lines['status_line'] = i
            key_lines['status_type'] = '运输中'
            break

    # 2. 电话号码行
    for i, line in enumerate(valid_lines):
        if re.search(r'\d{3}\*{4}\d{4}', line):
            key_lines['phone_line'] = i
            break

    # 3. 地址行
    if key_lines['phone_line'] != -1:
        start = key_lines['phone_line'] + 1
        end = min(key_lines['phone_line'] + 4, len(valid_lines))
        for i in range(start, end):
            line = valid_lines[i]
            if any(keyword in line for keyword in ['街道', '路', '号', '区', '市']):
                if re.search(r'\d+', line):
                    key_lines['address_line'] = i
                    break

    # 4. 店铺行
    if key_lines['address_line'] != -1:
        start = key_lines['address_line'] + 1
        end = min(key_lines['address_line'] + 6, len(valid_lines))
        for i in range(start, end):
            line = valid_lines[i]
            if ('店' in line or '旗舰店' in line or '专营店' in line) and len(line) <= 50:
                if not any(word in line for word in ['x1', '×1', '@', '¥', '￥']):
                    key_lines['store_line'] = i
                    break

    # 5. 按钮行
    for i, line in enumerate(valid_lines):
        if '分享商品' in line or '联系商家' in line:
            key_lines['buttons_line'] = i
            break

    # 6. 商品区域
    if key_lines['store_line'] != -1:
        key_lines['product_start'] = key_lines['store_line'] + 1
        if key_lines['buttons_line'] != -1:
            key_lines['product_end'] = key_lines['buttons_line'] - 1
        else:
            for i in range(key_lines['product_start'], min(key_lines['product_start'] + 8, len(valid_lines))):
                line = valid_lines[i]
                if '@' in line or re.search(r'[¥￥]\d+', line):
                    key_lines['product_end'] = i - 1
                    break
            if key_lines['product_end'] == -1:
                key_lines['product_end'] = min(key_lines['product_start'] + 6, len(valid_lines) - 1)

    # 7. 商品价格行
    for i, line in enumerate(valid_lines):
        if re.search(r'\d+\.?\d*\s*@', line):
            key_lines['price_line'] = i
            break

    # 8. 实付金额行
    for i, line in enumerate(valid_lines):
        if '实付' in line or '先用后付实付' in line:
            key_lines['real_pay_line'] = i
            break

    # 9. 订单信息开始
    for i, line in enumerate(valid_lines):
        if '订单编号' in line:
            key_lines['order_start'] = i
            break

    return key_lines, valid_lines


# ========== 改进的信息提取 ==========
def extract_pdd_info(lines, key_lines, valid_lines):
    """提取拼多多订单信息"""
    result = {
        '订单编号': '',
        '商品名称': '',
        '商品规格': '',
        '商品价格': '',
        '实付金额': '',
        '支付方式': '',
        '物流公司': '',
        '快递单号': '',
        '订单状态': '',
        '收件人': '',
        '联系方式': '',
        '收货地址': '',
        '店铺名称': '',
        '下单时间': '',
        '拼单时间': '',
        '发货时间': ''
    }

    # 1. 订单状态
    if 'status_type' in key_lines:
        result['订单状态'] = key_lines['status_type']

    # 2. 联系方式和收件人
    if key_lines['phone_line'] != -1:
        line = valid_lines[key_lines['phone_line']]
        phone_match = re.search(r'(1[3-9]\d\*{4}\d{4})', line)
        if phone_match:
            result['联系方式'] = phone_match.group(1)

            phone_pos = line.find(phone_match.group(1))
            if phone_pos > 0:
                before_phone = line[:phone_pos].strip()
                name_candidates = re.findall(r'[\u4e00-\u9fff]{2,4}', before_phone)
                for name in name_candidates:
                    if name not in ['待取件', '已签收', '运输中', '昨天', '今天', '小时', '分钟', '驿站', '取件码']:
                        result['收件人'] = name
                        break

        if not result['收件人'] and key_lines['phone_line'] > 0:
            prev_line = valid_lines[key_lines['phone_line'] - 1]
            name_match = re.search(r'([\u4e00-\u9fff]{2,4})', prev_line)
            if name_match:
                candidate = name_match.group(1)
                if candidate not in ['待取件', '已签收', '运输中', '昨天', '今天']:
                    result['收件人'] = candidate

    # 3. 收货地址
    if key_lines['address_line'] != -1:
        line = valid_lines[key_lines['address_line']]
        cleaned = re.sub(r'\d{3}\*{4}\d{4}', '', line)
        cleaned = re.sub(r'1[3-9]\d{9}', '', cleaned)
        cleaned = re.sub(r'[展开▼>»@$&*]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if result['收件人'] and result['收件人'] in cleaned:
            cleaned = cleaned.replace(result['收件人'], '').strip()

        if len(cleaned) >= 8:
            result['收货地址'] = cleaned

    # 4. 店铺名称
    if key_lines['store_line'] != -1:
        line = valid_lines[key_lines['store_line']]
        if '>' in line:
            parts = line.split('>')
            store_name = parts[0].strip()
        else:
            store_name = line.strip()

        store_name = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9\s]', ' ', store_name)
        store_name = re.sub(r'\s+', ' ', store_name).strip()
        store_name = re.sub(r'\d+\.?\d*[¥￥]?', '', store_name)
        store_name = re.sub(r'[×*xX]\s*\d+', '', store_name)

        if 2 <= len(store_name) <= 40:
            result['店铺名称'] = store_name

    # 5. 商品信息
    if key_lines['product_start'] != -1 and key_lines['product_end'] != -1:
        start = key_lines['product_start']
        end = min(key_lines['product_end'] + 1, len(valid_lines))

        product_lines = []
        for i in range(start, end):
            line = valid_lines[i]
            if any(word in line for word in ['分享商品', '联系商家', '申请售后', '7天无理由退货', '退货包运费']):
                continue
            product_lines.append(line)

        # 商品名称
        if product_lines:
            first_line = product_lines[0]
            cleaned = first_line
            cleaned = re.sub(r'[¥￥]\s*\d+\.?\d*', '', cleaned)
            cleaned = re.sub(r'\d+\.?\d*\s*@', '', cleaned)
            cleaned = re.sub(r'v\d+\.?\d*', '', cleaned)
            cleaned = re.sub(r'[×*xX]\s*\d+', '', cleaned)
            cleaned = re.sub(r'【[^】]+】', '', cleaned)
            cleaned = re.sub(r'\[[^\]]+\]', '', cleaned)
            cleaned = re.sub(r'[^\u4e00-\u9fffa-zA-Z0-9\s]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            if len(cleaned) < 4 and len(product_lines) > 1:
                second_line = product_lines[1]
                cleaned = re.sub(r'[¥￥@\d.\s×*xX]', '', second_line)
                cleaned = re.sub(r'[^\u4e00-\u9fffa-zA-Z]', ' ', cleaned)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            if cleaned and len(cleaned) >= 4:
                parts = cleaned.split()
                if len(parts) >= 2:
                    result['商品名称'] = ' '.join(parts[:min(4, len(parts))])

            # 商品规格
            specs = []
            for line in product_lines:
                bracket_specs = re.findall(r'【([^】]{2,30})】', line)
                specs.extend(bracket_specs)

                capacity_specs = re.findall(r'(\d+\s*[mMlLgG克毫升]{1,2})', line)
                for spec in capacity_specs:
                    if len(spec) >= 2 and not re.match(r'^\d+$', spec):
                        specs.append(spec)

                quantity_specs = re.findall(r'(\d+\s*[支瓶包条盒只个]{1})', line)
                specs.extend(quantity_specs)

                combo_specs = re.findall(r'(\d+[a-zA-Z]+\s*,\s*\d+[^,，;\s]+)', line)
                specs.extend(combo_specs)

            unique_specs = []
            for spec in specs:
                spec = spec.strip()
                if spec and spec not in unique_specs:
                    unique_specs.append(spec)

            if unique_specs:
                result['商品规格'] = '; '.join(unique_specs[:3])

    # 6. 商品价格
    if key_lines['price_line'] != -1:
        line = valid_lines[key_lines['price_line']]
        price_match = re.search(r'(\d+\.?\d*)\s*@', line)
        if price_match:
            price_str = price_match.group(1)
            try:
                if price_str.isdigit() and len(price_str) == 3:
                    price_float = float(f"{price_str[0]}.{price_str[1:]}")
                else:
                    price_float = float(price_str)

                if 0.01 <= price_float <= 9999.99:
                    result['商品价格'] = f"{price_float:.2f}"
            except:
                pass

    # 7. 实付金额
    if key_lines['real_pay_line'] != -1:
        line = valid_lines[key_lines['real_pay_line']]

        if '先用后付实付' in line:
            result['实付金额'] = '0.00'
        else:
            patterns = [
                (r'实付[:：]\s*[¥￥]?\s*(\d+\.?\d*)', 1),
                (r'[¥￥]\s*(\d+\.?\d*)\s*\(', 1),
                (r'(\d+\.\d{2})\s*@', 1),
            ]

            for pattern, group_idx in patterns:
                match = re.search(pattern, line)
                if match:
                    price_str = match.group(group_idx)
                    try:
                        price_float = float(price_str)
                        result['实付金额'] = f"{price_float:.2f}"
                        break
                    except:
                        continue

            if not result['实付金额']:
                if '¥0' in line or 'xO' in line or 'yxO' in line:
                    result['实付金额'] = '0.00'

    # 8. 订单详细信息
    if key_lines['order_start'] != -1:
        order_start = key_lines['order_start']
        order_end = min(order_start + 15, len(valid_lines))

        order_lines = valid_lines[order_start:order_end]

        for line in order_lines:
            # 订单编号
            if '订单编号' in line:
                match = re.search(r'(\d{6}-\d{9,15})', line)
                if match:
                    result['订单编号'] = match.group(1)

            # 支付方式
            if '支付方式' in line:
                if '先用后付' in line:
                    result['支付方式'] = '先用后付'
                elif '支付宝' in line:
                    result['支付方式'] = '支付宝'
                elif '微信' in line:
                    result['支付方式'] = '微信支付'
                elif 'RR' in line:
                    result['支付方式'] = '先用后付'

            # 物流公司
            if '物流公司' in line:
                identified_company = identify_logistics_company(line)
                if identified_company:
                    result['物流公司'] = identified_company
                else:
                    if '韵达' in line:
                        result['物流公司'] = '韵达'
                    elif '申通' in line:
                        result['物流公司'] = '申通'
                    elif '圆通' in line:
                        result['物流公司'] = '圆通'
                    elif '中通' in line:
                        result['物流公司'] = '中通'
                    elif '邮政' in line or '快递包' in line:
                        result['物流公司'] = '邮政'
                    elif '顺丰' in line:
                        result['物流公司'] = '顺丰'

            # 快递单号
            if '快递单号' in line:
                patterns = [
                    r'(\d{10,20})',
                    r'(YT\d{12,14})',
                    r'(464\d{12})',
                    r'(777\d{12})',
                    r'(981\d{12})',
                    r'(785\d{12})',
                    r'(SF\d{12,15})',
                    r'(JD\d{12,15})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        result['快递单号'] = match.group(1)
                        break

            # 时间信息
            time_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})', line)
            if time_match:
                time_str = time_match.group(1)
                if '下单时间' in line:
                    result['下单时间'] = time_str
                elif '拼单时间' in line:
                    result['拼单时间'] = time_str
                elif '发货时间' in line:
                    result['发货时间'] = time_str
                elif '拼音时间' in line:
                    result['拼单时间'] = time_str

    # 9. 如果没有通过标签找到时间，扫描所有行
    if not result['发货时间']:
        for line in valid_lines:
            time_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{1,2}:\d{1,2})', line)
            if time_match and '下单' not in line and '拼单' not in line:
                time_str = time_match.group(1)
                if time_str not in [result['下单时间'], result['拼单时间']]:
                    result['发货时间'] = time_str
                    break

    # 10. 后处理和验证
    for key in result:
        if result[key]:
            result[key] = re.sub(r'\s+', ' ', str(result[key])).strip()
            result[key] = re.sub(r'^[^a-zA-Z0-9\u4e00-\u9fff]+|[^a-zA-Z0-9\u4e00-\u9fff]+$', '', result[key])

    # 根据快递单号推断物流公司
    if not result['物流公司'] and result['快递单号']:
        identified_company = identify_logistics_by_tracking(result['快递单号'])
        if identified_company:
            result['物流公司'] = identified_company
        else:
            tracking = result['快递单号']
            if tracking.startswith('464'):
                result['物流公司'] = '韵达'
            elif tracking.startswith('777'):
                result['物流公司'] = '申通'
            elif tracking.startswith('YT') or tracking.startswith('88'):
                result['物流公司'] = '圆通'
            elif tracking.startswith('78'):
                result['物流公司'] = '中通'
            elif tracking.startswith('981'):
                result['物流公司'] = '邮政'
            elif tracking.startswith('SF'):
                result['物流公司'] = '顺丰'
            elif tracking.startswith('JD'):
                result['物流公司'] = '京东'

    # 如果商品价格还是没找到，但实付金额有值且不为0，可能是同一价格
    if not result['商品价格'] and result['实付金额'] and result['实付金额'] != '0.00':
        result['商品价格'] = result['实付金额']

    return result


# ========== 主提取函数 ==========
def extract_pdd_order_info(ocr_text):
    """提取拼多多订单信息"""
    # 清理文本
    clean_text = clean_ocr_text(ocr_text)
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]

    print("\n" + "=" * 80)
    print("📄 OCR识别文本:")
    print("=" * 80)
    for i, line in enumerate(lines[:30]):
        print(f"{i + 1:03d}: {line}")
    if len(lines) > 30:
        print(f"... 还有 {len(lines) - 30} 行")
    print("=" * 80)

    # 分析布局
    print("🔍 分析布局结构...")
    key_lines, valid_lines = analyze_pdd_layout(lines)

    # 打印关键行
    print("📊 关键行位置:")
    for key, value in key_lines.items():
        if value != -1 and key != 'status_type':
            line_preview = valid_lines[value][:40] if value < len(valid_lines) else ""
            print(f"  {key:15}: 行 {value:2d} - {line_preview}...")

    # 提取信息
    print("🔧 提取订单信息...")
    result = extract_pdd_info(lines, key_lines, valid_lines)

    # 打印结果
    print("\n" + "=" * 80)
    print("📋 提取结果:")
    print("=" * 80)
    for key, value in result.items():
        if value:
            print(f"  {key:8}: {value}")
        else:
            print(f"  {key:8}: ❌ 未找到")

    extracted_count = sum(1 for v in result.values() if v)
    print(f"\n✅ 提取到 {extracted_count}/16 个字段")
    print("=" * 80)

    return result


# ========== Flask接口 ==========
@app.route('/pic', methods=['POST'])
def pic():
    """拼多多订单图片OCR提取接口"""
    image_path = None
    temp_file_created = False

    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '请求中未包含图片文件'
            }), 400

        image_file = request.files['image']
        if not image_file or image_file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件无效或文件名为空'
            }), 400

        filename = image_file.filename
        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext not in SUPPORTED_IMAGE_FORMATS:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式: {file_ext}',
                'supported_formats': list(SUPPORTED_IMAGE_FORMATS)
            }), 400

        temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        os.makedirs(temp_dir, exist_ok=True)

        timestamp = int(time.time())
        random_id = uuid.uuid4().hex[:8]
        temp_filename = f"pdd_{timestamp}_{random_id}{file_ext}"
        image_path = os.path.join(temp_dir, temp_filename)
        image_file.save(image_path)
        temp_file_created = True

        # OCR处理
        print(f"\n🔄 开始处理图片: {filename}")

        image = Image.open(image_path)
        processed_image = preprocess_image(image)

        print("🔍 进行OCR识别...")

        config = '--psm 6 --oem 3'
        text = pytesseract.image_to_string(
            processed_image,
            lang='chi_sim+eng',
            config=config
        )

        non_empty_lines = [l for l in text.split('\n') if l.strip()]
        print(f"📝 OCR结果: {len(non_empty_lines)} 行文本")
        print(non_empty_lines)

        # 提取信息
        extracted_data = extract_pdd_order_info(text)
        print(extracted_data)
        extracted_count = sum(1 for v in extracted_data.values() if v)

        response_data = {
            'success': True,
            'data': extracted_data,
            'message': f'成功提取 {extracted_count}/16 个字段',
            'extracted_count': extracted_count,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        print(response_data)

        return jsonify(response_data)

    except Exception as e:
        error_msg = f"OCR处理失败: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'error': error_msg,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }), 500
    finally:
        if temp_file_created and image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                print(f"🧹 清理临时文件: {image_path}")
            except:
                pass


@app.route('/')
def index():
    return '''
    <html>
        <head><title>拼多多订单OCR提取服务</title></head>
        <body>
            <h1>拼多多订单OCR提取服务</h1>
            <p>使用POST /pic接口上传订单截图</p>
        </body>
    </html>
    '''


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)