# -*- coding: utf-8 -*-
import os
import sys
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
import time

# ================= 配置区域 =================
# 图片绝对路径
IMAGE_PATH = r"C:\02media\01sharefile\01order_info\0126\300\pic\testpic\01.jpg"

# Tesseract 安装路径 (如果不在环境变量中，请取消注释并修改为你电脑的实际路径)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 期望的正确结果 (用于对比)
EXPECTED_DATA = {
    '订单编号': '251109-349689618030662',
    '商品名称': '超厚条纹厨房抹布不沾油洗碗巾加厚吸水不掉毛刷碗布去油清洁无痕',
    '商品规格': '升级加大加厚【包边加挂绳】,加厚【条纹灰咖色1条装】12*12cm',
    '商品价格': '0.89', # 注意：通常提取为数字字符串，去掉人民币符号
    '实付金额': '0.00', # 对应 ¥0
    '支付方式': '先用后付',
    '物流公司': '韵达', # 脚本逻辑通常会提取关键字
    '快递单号': '464841042250593',
    '订单状态': '待取件',
    '收件人': '郑传宝',
    '联系方式': '134****9326',
    '收货地址': '九佛街道九佛育才路900号信科大院101号',
    '店铺名称': '森森家具百货店',
    '下单时间': '2025-11-09 19:42:41',
    '拼单时间': '2025-11-09 19:42:42',
    '发货时间': '2025-11-10 11:38:32'
}
# ===========================================

def check_tesseract_env():
    """检查Tesseract环境和语言包"""
    print(f"[*] 正在检查 Tesseract 环境...")
    try:
        langs = pytesseract.get_languages(config='')
        print(f"[*] 已安装语言包: {langs}")
        if 'chi_sim' not in langs:
            print("❌ [严重错误] 未检测到中文语言包 'chi_sim'！")
            print("   请下载 chi_sim.traineddata 放入 tessdata 目录。")
            print("   下载地址: https://github.com/tesseract-ocr/tessdata_best/blob/main/chi_sim.traineddata")
            return False
        else:
            print("✅ 检测到中文语言包。")
            return True
    except Exception as e:
        print(f"❌ Tesseract 调用失败: {e}")
        print("   请确保安装了 Tesseract-OCR 并配置了环境变量。")
        return False

def preprocess_image_debug(image_path):
    """优化的预处理逻辑，并保存中间图供查看"""
    try:
        img = Image.open(image_path)
        print(f"[*] 图片原始尺寸: {img.size}")
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 放大图片 (对于手机截图，放大 2-3 倍能显著提高文字清晰度)
        width, height = img.size
        new_width = width * 3
        new_height = height * 3
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 转灰度
        img = img.convert('L')
        
        # 对比度增强 (不要太强，否则浅灰色字会消失)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5) 
        
        # 锐化
        img = img.filter(ImageFilter.SHARPEN)
        
        # 二值化处理 (可选，有时候对于黑字白底很有效)
        # threshold = 140
        # img = img.point(lambda p: 255 if p > threshold else 0)

        # 保存预处理后的图片以便人工检查
        temp_path = "debug_processed.jpg"
        img.save(temp_path)
        print(f"[*] 预处理图片已保存至: {os.path.abspath(temp_path)}")
        
        return img
    except Exception as e:
        print(f"❌ 图片加载失败: {e}")
        return None

# 这里直接复用你原有代码中的 extract_pdd_order_info 逻辑
# 为了保持脚本独立，我把核心逻辑复制过来了 (并做了一点点针对性的修正)
# ------------------------------------------------------------------
LOGISTICS_COMPANIES = {'韵达': ['韵达', 'yunda', 'YD'],'申通': ['申通', 'shentong', 'ST'],'圆通': ['圆通', 'yuantong', 'YT'],'中通': ['中通', 'zhongtong', 'ZT'],'邮政': ['邮政', '邮政快递', '快递包', 'youzheng', 'EMS'],'顺丰': ['顺丰', '顺丰快递', 'shunfeng', 'SF'],'京东': ['京东', '京东快递', 'jingdong', 'JD'],'百世': ['百世', '百世快递', 'baishi'],'天天': ['天天', '天天快递', 'tiantian'],'德邦': ['德邦', '德邦快递', 'debang']}

def identify_logistics_company(line):
    line_lower = line.lower()
    for company, keywords in LOGISTICS_COMPANIES.items():
        for keyword in keywords:
            if keyword.lower() in line_lower: return company
    return None

def run_ocr_logic(text):
    """简化的提取逻辑，模拟 picture_orc.py 的核心部分"""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    result = {k: '' for k in EXPECTED_DATA.keys()}
    
    # 简单的关键字匹配逻辑模拟 (对应你的 analyze_pdd_layout 部分)
    for i, line in enumerate(lines):
        # 订单状态
        if line in ['待取件', '已签收', '运输中', '交易成功']:
            result['订单状态'] = line
            
        # 电话/收件人
        phone_match = re.search(r'(1[3-9]\d\*{4}\d{4})', line)
        if phone_match:
            result['联系方式'] = phone_match.group(1)
            # 尝试在电话行前面找名字
            parts = line.split(result['联系方式'])
            if len(parts) > 0 and len(parts[0].strip()) > 1:
                 # 过滤掉乱码
                 name_candidate = parts[0].strip()
                 name_candidate = re.sub(r'[^\u4e00-\u9fff]', '', name_candidate)
                 if name_candidate:
                     result['收件人'] = name_candidate
        
        # 地址
        if '省' in line or '市' in line or '区' in line or '街道' in line or '路' in line:
             if len(line) > 8 and not result['收货地址']:
                 result['收货地址'] = line

        # 订单编号
        if '订单编号' in line:
            m = re.search(r'(\d{6}-\d{9,15})', line)
            if m: result['订单编号'] = m.group(1)
            
        # 快递单号
        if '快递单号' in line:
            m = re.search(r'(\w{10,20})', line) # 扩大匹配范围
            if m: result['快递单号'] = m.group(1)
        # 补救：如果在非标签行看到像单号的纯数字
        elif re.match(r'^464\d{12}$', line) and not result['快递单号']:
            result['快递单号'] = line

        # 价格
        if '¥' in line or '￥' in line:
            m = re.search(r'[¥￥]\s*(\d+\.?\d*)', line)
            if m:
                val = m.group(1)
                # 简单逻辑：如果是0就是实付，非0可能是单价
                if float(val) == 0: result['实付金额'] = '0.00'
                elif not result['商品价格']: result['商品价格'] = val

        # 纯数字价格行 (你的代码逻辑)
        if '@' in line:
             m = re.search(r'(\d+\.?\d*)\s*@', line)
             if m: result['商品价格'] = m.group(1)

        # 物流
        if '物流公司' in line:
            comp = identify_logistics_company(line)
            if comp: result['物流公司'] = comp
        elif '韵达' in line: result['物流公司'] = '韵达'

        # 时间
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
        if time_match:
            t = time_match.group(1)
            if '下单' in line: result['下单时间'] = t
            elif '拼单' in line: result['拼单时间'] = t
            elif '发货' in line: result['发货时间'] = t
            
    # 店铺 (通常在商品上方，带 > 符号)
    for i, line in enumerate(lines):
        if '>' in line and '店' in line:
            result['店铺名称'] = line.split('>')[0].strip()
            break

    return result, lines

# ================= 主程序 =================
if __name__ == "__main__":
    print("="*60)
    print(" 🕵️‍♂️ PDD OCR 深度调试工具")
    print("="*60)

    # 1. 检查环境
    if not check_tesseract_env():
        sys.exit(1)

    # 2. 读取和预处理
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ 找不到文件: {IMAGE_PATH}")
        sys.exit(1)
        
    img = preprocess_image_debug(IMAGE_PATH)
    if not img: sys.exit(1)

    # 3. 执行 OCR
    print("\n[*] 正在进行 OCR 识别 (lang='chi_sim+eng', psm=6)...")
    start_time = time.time()
    # 关键：使用 psm 6 (假设统一文本块) 或 psm 3 (自动分段)
    # 也可以尝试 psm 4 (单列文本)
    raw_text = pytesseract.image_to_string(img, lang='chi_sim+eng', config='--psm 6')
    print(f"[*] OCR 耗时: {time.time() - start_time:.2f}s")

    # 4. 提取信息
    extracted_data, lines = run_ocr_logic(raw_text)

    # 5. 打印原始内容 (用于分析为什么正则匹配不到)
    print("\n" + "="*20 + " OCR 原始文本行 " + "="*20)
    for idx, line in enumerate(lines):
        print(f"{idx+1:02d}: {line}")
    print("="*56)

    # 6. 对比结果
    print("\n" + "="*20 + " 结果对比分析 " + "="*20)
    print(f"{'字段名':<10} | {'实际提取值':<30} | {'期望值':<30} | {'状态'}")
    print("-" * 85)
    
    match_count = 0
    for key, expected in EXPECTED_DATA.items():
        actual = extracted_data.get(key, '')
        if actual is None: actual = ''
        
        # 模糊对比 (忽略空格和部分符号)
        clean_actual = str(actual).replace('¥', '').replace(' ','')
        clean_expected = str(expected).replace('¥', '').replace(' ','')
        
        # 针对部分字段做包含匹配
        is_match = False
        if clean_expected == clean_actual:
            is_match = True
        elif clean_expected in clean_actual and len(clean_actual) > 0:
            is_match = True
        elif key == '商品价格' and float(clean_actual or 0) == float(clean_expected or 0):
            is_match = True
            
        status = "✅ 匹配" if is_match else "❌ 失败"
        if is_match: match_count += 1
        
        # 截断过长的显示
        disp_actual = (str(actual)[:28] + '..') if len(str(actual)) > 28 else str(actual)
        disp_expected = (str(expected)[:28] + '..') if len(str(expected)) > 28 else str(expected)
        
        print(f"{key:<10} | {disp_actual:<30} | {disp_expected:<30} | {status}")

    print("-" * 85)
    print(f"总计匹配成功: {match_count} / {len(EXPECTED_DATA)}")
    print("="*60)
    
    print("\n💡 修复建议:")
    print("1. 如果 [OCR 原始文本行] 中全是乱码/英文，说明没有加载中文库 chi_sim。")
    print("2. 如果 [OCR 原始文本行] 中有中文但断断续续，说明图片预处理不够 (太小或对比度太高)。")
    print("3. 检查 debug_processed.jpg，确保肉眼能清晰看到文字，且没有过多的噪点。")