"""
数据库和应用的共享配置
"""

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'db_order',
    'charset': 'utf8mb4'
}

# Flask应用配置
APP_CONFIG = {
    'debug': True,
    'host': '0.0.0.0',
    'port': 5000
}

# OCR参数配置
OCR_CONFIG = {
    'supported_formats': {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'},
    'tesseract_config': '--psm 6 --oem 3',
    'min_dimension': 1200
}