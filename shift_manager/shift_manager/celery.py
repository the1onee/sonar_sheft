from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')

REDIS_URL = "rediss://default:ASm7AAIncDJkNTNkZjgyNjVhMzQ0N2U3ODUzMGZiMjZhYmVmMmU4ZnAyMTA2ODM@chief-firefly-10683.upstash.io:6379/0?ssl_cert_reqs=CERT_NONE"

app = Celery('shift_manager', broker=REDIS_URL, backend=REDIS_URL)

app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.timezone = 'Asia/Baghdad'
app.conf.enable_utc = True

app.autodiscover_tasks()
