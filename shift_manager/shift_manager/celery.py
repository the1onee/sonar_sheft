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
app.conf.beat_schedule = {
    # مهمة التبديل التلقائي - كل 3 ساعات (افتراضي)
    'rotate-shifts-default': {
        'task': 'shifts.tasks.rotate_shifts_task',
        'schedule': timedelta(hours=3),
    },
    # مهمة فحص الإشعارات المبكرة - كل دقيقتين
    'check-early-notifications': {
        'task': 'shifts.tasks.check_early_notifications_task',
        'schedule': crontab(minute='*/2'),
    },
    # مهمة رفض التبديلات المنتهية (التي لم يؤكدها الموظف) - كل 10 دقائق
    'cancel-expired-confirmations': {
        'task': 'shifts.tasks.cancel_expired_confirmations_task',
        'schedule': crontab(minute='*/10'),
    },
}

app.autodiscover_tasks()
