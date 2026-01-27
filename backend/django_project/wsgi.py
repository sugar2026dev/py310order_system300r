import os
import sys

# 🔥 关键：在导入Django前设置路径
project_root = '/opt/order_system/backend'
django_project_path = os.path.join(project_root, 'django_project')
apps_path = os.path.join(project_root, 'apps')

print(f"Python路径设置:")
print(f"  1. {django_project_path}")
print(f"  2. {apps_path}")
print(f"  3. {project_root}")

# 添加到Python路径（确保顺序正确）
if django_project_path not in sys.path:
    sys.path.insert(0, django_project_path)
if apps_path not in sys.path:
    sys.path.insert(0, apps_path)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

application = get_wsgi_application()
