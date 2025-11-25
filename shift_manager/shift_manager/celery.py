from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import os
from dotenv import load_dotenv

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')

# تحميل ملف .env
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# قراءة REDIS_URL من ملف .env
REDIS_URL = os.getenv(
    'REDIS_URL',
    'rediss://default:ASm7AAIncDJkNTNkZjgyNjVhMzQ0N2U3ODUzMGZiMjZhYmVmMmU4ZnAyMTA2ODM@chief-firefly-10683.upstash.io:6379/0?ssl_cert_reqs=CERT_NONE'
)

app = Celery('shift_manager', broker=REDIS_URL, backend=REDIS_URL)

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Asia/Baghdad'
app.conf.enable_utc = True

# الجدولة الأساسية لـ Celery Beat
# ملاحظة: يتم تحديث هذه الجدولة ديناميكياً من خلال update_celery_schedule() في views.py
# الجدولة الافتراضية (يتم تحديثها عند تغيير الإعدادات)
app.conf.beat_schedule = {
    # مهمة فحص الإشعارات المبكرة - كل 5 دقائق (افتراضي، يتم تحديثه ديناميكياً)
    'check-early-notifications': {
        'task': 'shifts.tasks.check_early_notifications_task',
        'schedule': crontab(),  # كل دقيقة مبدئياً (يتم تعديلها ديناميكياً لاحقاً)
    },
    # مهمة التبديل التلقائي - سيتم إضافتها ديناميكياً من update_celery_schedule()
    # مهمة تصفير ساعات العمل الشهرية - أول يوم من كل شهر في منتصف الليل
    'reset-monthly-work-hours': {
        'task': 'shifts.tasks.reset_monthly_work_hours',
        'schedule': crontab(minute=0, hour=0, day_of_month=1),  # الساعة 00:00 في اليوم الأول من كل شهر
    },
}

app.autodiscover_tasks()

# تحديث الجدولة بمجرد بدء Celery (لتفادي الاعتماد على لوحة الإعدادات فقط)
try:
    from shifts.views import update_celery_schedule
    update_celery_schedule()
except Exception as exc:
    print(f"⚠️ تعذر تحديث جدولة Celery تلقائياً: {exc}")
