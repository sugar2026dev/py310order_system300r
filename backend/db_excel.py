import pymysql
import json
import os
import shutil
from datetime import datetime
from config import DB_CONFIG


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def save_ocr_data(ocr_result, extracted_data, image_path, upload_user='ocr_user'):
    """保存OCR数据到数据库"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 提取订单编码
        order_code = extract_order_code(extracted_data)

        print(f"🔍 准备保存数据:")
        print(f"   订单编号: {order_code}")

        if not order_code:
            cursor.close()
            conn.close()
            return {
                'success': False,
                'error': '未提取到订单编号'
            }

        # 检查重复
        cursor.execute("SELECT id FROM order_info WHERE order_code = %s", (order_code,))
        existing = cursor.fetchone()

        if existing:
            print(f"ℹ️  Flask端: 订单 {order_code} 已存在 (ID: {existing[0]})")
            cursor.close()
            conn.close()
            # 重要：只返回信息，不标记为duplicate
            return {
                'success': True,
                'order_code': order_code,
                'existing_id': existing[0],
                'message': f'订单 {order_code} 已存在于Flask数据库',
                'note': 'Flask端检测到重复，请Django端确认'
            }

        # 如果到这里，说明是新订单，继续保存流程
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 处理图片
        img_filename = ""
        img_path = ""

        if image_path and os.path.exists(image_path):
            try:
                original_filename = os.path.basename(image_path)
                _, img_extension = os.path.splitext(image_path)
                img_extension = img_extension.lower()

                if img_extension not in {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}:
                    img_extension = '.jpg'

                # 生成文件名
                timestamp_date = datetime.now().strftime('%Y%m%d')
                base_name = f"{order_code}_{timestamp_date}"
                img_filename = f"{base_name}{img_extension}"

                # 创建图片目录
                img_dir = "media/order_images"
                if not os.path.exists(img_dir):
                    os.makedirs(img_dir)

                # 完整路径
                img_path = os.path.join(img_dir, img_filename)

                # 复制图片
                shutil.copy2(image_path, img_path)

                print(f"📸 图片保存成功: {img_filename}")

            except Exception as e:
                print(f"⚠️ 图片处理失败: {e}")
                img_filename = os.path.basename(image_path)
                img_path = image_path

        # 序列化数据
        try:
            data_json = json.dumps(extracted_data, ensure_ascii=False)
        except Exception as e:
            print(f"❌ JSON序列化失败: {e}")
            data_json = json.dumps({})

        # 插入数据库
        cursor.execute(
            """
            INSERT INTO order_info 
            (order_code, upload_user, ocr_result, extracted_data, 
             img_filename, img_path, create_time, update_time) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order_code,
                upload_user,
                json.dumps(ocr_result, ensure_ascii=False),
                data_json,
                img_filename,
                img_path,
                current_time,
                current_time
            )
        )

        conn.commit()
        data_id = cursor.lastrowid

        cursor.close()
        conn.close()

        print(f"✅ 新订单保存成功! ID: {data_id}, 订单编号: {order_code}")

        return {
            'success': True,
            'id': data_id,
            'order_code': order_code,
            'message': '数据保存成功'
        }

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def extract_order_code(extracted_data):
    """从提取的数据中获取订单编码"""
    try:
        order_code_fields = ['订单编号', '订单编码', 'order_code', 'order_number']

        for field in order_code_fields:
            if field in extracted_data and extracted_data[field]:
                return extracted_data[field]

        return None
    except Exception as e:
        print(f"提取订单编码失败: {e}")
        return None