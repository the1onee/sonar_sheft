"""
سكريبت اختبار Celery - تشغيله للتأكد من عمل Celery
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')
django.setup()

from shifts.tasks import rotate_shifts_task, check_early_notifications_task
from shifts.models import SystemSettings
from celery import current_app

print("=" * 50)
print("اختبار Celery - نظام إدارة السونار")
print("=" * 50)
print()

# 1. التحقق من اتصال Celery
print("📡 [1/5] فحص اتصال Celery...")
try:
    # محاولة ping لـ Celery
    inspector = current_app.control.inspect()
    active = inspector.active()
    
    if active:
        print("✅ Celery Worker متصل ويعمل!")
        print(f"   عدد الـ Workers النشطة: {len(active)}")
        for worker_name in active.keys():
            print(f"   - {worker_name}")
    else:
        print("❌ لا يوجد Workers نشطة!")
        print("   تأكد من تشغيل: celery -A shift_manager worker")
except Exception as e:
    print(f"❌ خطأ في الاتصال بـ Celery: {e}")
    print("   تأكد من تشغيل Redis و Celery Worker")

print()

# 2. التحقق من Redis
print("🔴 [2/5] فحص اتصال Redis...")
try:
    from celery import current_app
    result = current_app.backend.client.ping()
    if result:
        print("✅ Redis متصل ويعمل!")
    else:
        print("❌ Redis غير متصل!")
except Exception as e:
    print(f"❌ خطأ في الاتصال بـ Redis: {e}")

print()

# 3. فحص الإعدادات
print("⚙️  [3/5] فحص إعدادات النظام...")
try:
    settings = SystemSettings.get_current_settings()
    print(f"✅ الإعدادات محملة:")
    print(f"   - فترة التبديل: {settings.rotation_interval_hours} ساعة")
    print(f"   - الإشعار المبكر: {settings.early_notification_minutes} دقيقة")
    print(f"   - حالة التبديل: {'🟢 نشط' if settings.is_rotation_active else '🔴 متوقف'}")
except Exception as e:
    print(f"❌ خطأ في تحميل الإعدادات: {e}")

print()

# 4. فحص الجدولة (Beat Schedule)
print("📅 [4/5] فحص جدولة المهام (Beat Schedule)...")
try:
    schedule = current_app.conf.beat_schedule
    print(f"✅ عدد المهام المجدولة: {len(schedule)}")
    for task_name, task_info in schedule.items():
        print(f"   - {task_name}")
        print(f"     المهمة: {task_info['task']}")
        if 'schedule' in task_info:
            schedule_info = task_info['schedule']
            if hasattr(schedule_info, 'total_seconds'):
                hours = schedule_info.total_seconds() / 3600
                print(f"     التوقيت: كل {hours} ساعة")
            else:
                print(f"     التوقيت: {schedule_info}")
except Exception as e:
    print(f"❌ خطأ في فحص الجدولة: {e}")

print()

# 5. اختبار تنفيذ مهمة
print("🧪 [5/5] اختبار تنفيذ مهمة الإشعارات...")
try:
    # تنفيذ مهمة فحص الإشعارات بشكل فوري
    result = check_early_notifications_task.delay()
    print(f"✅ تم إرسال المهمة بنجاح!")
    print(f"   Task ID: {result.id}")
    print(f"   الحالة: {result.state}")
    
    # الانتظار قليلاً والتحقق من النتيجة
    print("   جاري التنفيذ...", end="", flush=True)
    import time
    for i in range(3):
        time.sleep(1)
        print(".", end="", flush=True)
    print()
    
    if result.ready():
        print(f"   ✅ المهمة اكتملت!")
        if result.successful():
            print(f"   النتيجة: {result.result}")
        else:
            print(f"   ⚠️  حدث خطأ: {result.result}")
    else:
        print(f"   ⏳ المهمة لا تزال قيد التنفيذ...")
        
except Exception as e:
    print(f"❌ خطأ في تنفيذ المهمة: {e}")

print()
print("=" * 50)
print("انتهى الاختبار!")
print("=" * 50)
print()
print("📝 ملاحظات:")
print("   - إذا ظهرت جميع العلامات ✅ فكل شيء يعمل بشكل صحيح")
print("   - إذا ظهرت علامة ❌ راجع الرسالة وصحح المشكلة")
print("   - شاهد نافذة Celery Worker لرؤية تنفيذ المهام")
print()

