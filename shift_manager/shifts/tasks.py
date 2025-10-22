# shifts/tasks.py
from celery import shared_task
from datetime import time
from django.utils import timezone
from .models import Shift, Sonar, Employee, EmployeeAssignment
from .utils import rotate_within_shift, check_and_send_early_notifications
from .models import SystemSettings


@shared_task
def rotate_shifts_task(rotation_hours=None):
    # الحصول على إعدادات النظام
    settings = SystemSettings.get_current_settings()
    
    # التحقق من تفعيل التبديل التلقائي
    if not settings.is_rotation_active:
        print("🔕 التبديل التلقائي معطل من الإعدادات")
        return
    
    # التحقق من الوقت المناسب للتبديل
    from datetime import timedelta
    now = timezone.now()
    
    # إذا كان هناك آخر تبديل، نتحقق من الوقت المنقضي
    if settings.last_rotation_time:
        time_since_last = now - settings.last_rotation_time
        required_interval = timedelta(hours=settings.get_effective_rotation_hours())
        
        if time_since_last < required_interval:
            remaining_time = required_interval - time_since_last
            minutes_remaining = remaining_time.total_seconds() / 60
            print(f"⏳ لم يحن وقت التبديل بعد. متبقي: {minutes_remaining:.1f} دقيقة")
            return
    
    # استخدام الإعدادات المحفوظة
    rotation_hours = settings.get_effective_rotation_hours()
    print(f"📊 تنفيذ التبديل حسب الإعدادات: {rotation_hours} ساعة")
    
    # الحصول على الوقت الحالي بالمنطقة الزمنية المحلية (Asia/Baghdad)
    now_local = timezone.localtime(timezone.now()).time()

    # تعريف نطاقات الشفتات حسب الساعة (استخدام القيم الإنجليزية كما في قاعدة البيانات)
    shift_ranges = {
        "morning": (time(7, 0), time(15, 0)),    # صباحي
        "evening": (time(15, 0), time(23, 0)),   # مسائي
        "night": (time(23, 0), time(7, 0))       # ليلي
    }
    
    # أسماء الشفتات بالعربية للطباعة
    shift_labels = {
        "morning": "صباحي",
        "evening": "مسائي",
        "night": "ليلي"
    }

    # تحديد الشفت الحالي حسب الوقت
    current_shift_name = None
    for shift_name, (start, end) in shift_ranges.items():
        if start <= end:  # شفت عادي (صباحي، مسائي)
            if start <= now_local < end:
                current_shift_name = shift_name
                break
        else:  # شفت يمر منتصف الليل (ليلي من 23:00 إلى 07:00)
            if now_local >= start or now_local < end:
                current_shift_name = shift_name
                break

    if not current_shift_name:
        print("❌ لا يوجد شفت نشط حاليا")
        return

    # طباعة اسم الشفت بالعربية
    print(f"🔄 الشفت الحالي: {shift_labels.get(current_shift_name, current_shift_name)} ({now_local.strftime('%H:%M')})")

    # تنفيذ التدوير فقط للشفت الحالي
    try:
        rotate_within_shift(current_shift_name, rotation_hours)
        # تحديث وقت آخر تبديل
        settings.update_last_rotation_time()
        print(f"✅ تم التبديل بنجاح وتحديث آخر وقت تبديل")
    except Exception as e:
        print(f"❌ خطأ في شفت {shift_labels.get(current_shift_name, current_shift_name)}: {e}")


@shared_task
def check_early_notifications_task():
    """مهمة دورية لفحص وإرسال الإشعارات المبكرة"""
    try:
        check_and_send_early_notifications()
    except Exception as e:
        print(f"❌ خطأ في فحص الإشعارات المبكرة: {e}")