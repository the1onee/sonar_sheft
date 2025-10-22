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
    
    # الحصول على الوقت الحالي بالمنطقة الزمنية المحلية (Asia/Baghdad)
    from datetime import timedelta, datetime
    now = timezone.now()
    now_local = timezone.localtime(now)
    current_time = now_local.time()
    
    # تعريف أوقات نهاية الشفتات
    shift_end_times = {
        "night": time(7, 0),      # نهاية الليلي - بداية الصباحي
        "morning": time(15, 0),   # نهاية الصباحي - بداية المسائي  
        "evening": time(23, 0),   # نهاية المسائي - بداية الليلي
    }
    
    # تعريف نطاقات الشفتات حسب الساعة
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
    
    # تحديد الشفت الحالي
    current_shift_name = None
    for shift_name, (start, end) in shift_ranges.items():
        if start <= end:  # شفت عادي
            if start <= current_time < end:
                current_shift_name = shift_name
                break
        else:  # شفت يمر منتصف الليل
            if current_time >= start or current_time < end:
                current_shift_name = shift_name
                break
    
    if not current_shift_name:
        print("❌ لا يوجد شفت نشط حاليا")
        return
    
    # الحصول على ساعات التبديل من الإعدادات
    rotation_hours = settings.get_effective_rotation_hours()
    
    # 🔥 الأولوية الأولى: التحقق إذا كنا في نهاية الشيفت
    is_shift_end = False
    shift_to_rotate = None
    
    for shift_name, end_time in shift_end_times.items():
        # حساب الفرق بالدقائق من وقت نهاية الشيفت
        current_datetime = datetime.combine(now_local.date(), current_time)
        end_datetime = datetime.combine(now_local.date(), end_time)
        
        # معالجة حالة منتصف الليل
        if end_time.hour < 12 and current_time.hour >= 12:
            end_datetime += timedelta(days=1)
        
        time_diff = (end_datetime - current_datetime).total_seconds() / 60
        
        # إذا كنا في آخر 15 دقيقة من الشيفت أو مرت 5 دقائق من بدايته
        if -5 <= time_diff <= 15:
            is_shift_end = True
            shift_to_rotate = shift_name
            print(f"⏰ نهاية الشيفت! {shift_labels.get(shift_name)} | الوقت المتبقي: {time_diff:.1f} دقيقة | تبديل مباشر")
            
            # التحقق من عدم التبديل مرتين في نفس الفترة (كل 15 دقيقة على الأقل)
            if settings.last_rotation_time:
                time_since_last = now - settings.last_rotation_time
                if time_since_last < timedelta(minutes=15):
                    minutes_since = time_since_last.total_seconds() / 60
                    print(f"⏸️ تم التبديل مؤخراً ({minutes_since:.1f} دقيقة مضت). تجاهل...")
                    return
            
            # تنفيذ التبديل فوراً عند نهاية الشيفت
            try:
                rotate_within_shift(current_shift_name, rotation_hours)
                settings.update_last_rotation_time()
                print(f"✅ تبديل نهاية الشيفت: {shift_labels.get(shift_name)} → الشيفت التالي")
                return
            except Exception as e:
                print(f"❌ خطأ في تبديل نهاية الشيفت: {e}")
                return
    
    # 🔥 الأولوية الثانية: التحقق من الوقت المحدد (X ساعات)
    if settings.last_rotation_time:
        time_since_last = now - settings.last_rotation_time
        required_interval = timedelta(hours=rotation_hours)
        
        if time_since_last >= required_interval:
            # حان وقت التبديل حسب الإعدادات
            hours_since = time_since_last.total_seconds() / 3600
            print(f"⏱️ مر {hours_since:.1f} ساعة من آخر تبديل (المطلوب: {rotation_hours} ساعة)")
            
            try:
                rotate_within_shift(current_shift_name, rotation_hours)
                settings.update_last_rotation_time()
                print(f"✅ تبديل دوري: كل {rotation_hours} ساعة في شفت {shift_labels.get(current_shift_name)}")
                return
            except Exception as e:
                print(f"❌ خطأ في التبديل الدوري: {e}")
                return
        else:
            # لم يحن وقت التبديل بعد
            remaining_time = required_interval - time_since_last
            minutes_remaining = remaining_time.total_seconds() / 60
            print(f"⏳ لم يحن وقت التبديل بعد | متبقي: {minutes_remaining:.1f} دقيقة | شفت: {shift_labels.get(current_shift_name)}")
    else:
        # أول مرة يتم تشغيل النظام - نبدأ التبديل الآن
        print(f"🆕 أول تبديل في النظام - بدء التبديل في شفت {shift_labels.get(current_shift_name)}")
        try:
            rotate_within_shift(current_shift_name, rotation_hours)
            settings.update_last_rotation_time()
            print(f"✅ تم التبديل الأولي بنجاح")
        except Exception as e:
            print(f"❌ خطأ في التبديل الأولي: {e}")


@shared_task
def check_early_notifications_task():
    """مهمة دورية لفحص وإرسال الإشعارات المبكرة"""
    try:
        check_and_send_early_notifications()
    except Exception as e:
        print(f"❌ خطأ في فحص الإشعارات المبكرة: {e}")