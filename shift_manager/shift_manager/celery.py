from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')

# الحصول على REDIS_URL من متغيرات البيئة
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

app = Celery('shift_manager', broker=REDIS_URL, backend=REDIS_URL)

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = os.environ.get('TIMEZONE', 'Asia/Baghdad')
app.conf.enable_utc = True

# جدولة المهام التلقائية (Celery Beat)
app.conf.beat_schedule = {
    # فحص الإشعارات المبكرة والمتكررة كل 2 دقيقة
    # لضمان اصطياد كل نوافذ الإشعارات (30، 20، 10، 0 دقيقة)
    'check-early-notifications': {
        'task': 'shifts.tasks.check_early_notifications_task',
        'schedule': crontab(minute='*/2'),  # كل 2 دقيقة
    },
}

app.autodiscover_tasks()
