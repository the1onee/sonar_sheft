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
    lead_minutes = max(int(settings.early_notification_minutes or 30), 0)
    lead_delta = timedelta(minutes=lead_minutes)
    effective_now_local = now_local + lead_delta
    current_time = effective_now_local.time()
    
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
        current_datetime = datetime.combine(effective_now_local.date(), current_time)
        end_datetime = datetime.combine(effective_now_local.date(), end_time)
        
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
                rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=lead_minutes)
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
                rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=lead_minutes)
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
            rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=lead_minutes)
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


@shared_task
def reset_monthly_work_hours():
    """تصفير ساعات العمل لجميع الموظفين في بداية كل شهر
    
    ملاحظة: السجلات التاريخية (EmployeeAssignment) تبقى محفوظة للتقارير
    فقط ساعات العمل الإجمالية (total_work_hours) تُصفّر للبدء من جديد
    """
    from django.utils import timezone
    from django.contrib.auth.models import User
    from django.db import models
    
    print("\n" + "="*70)
    print("🔄 بدء عملية تصفير ساعات العمل الشهرية")
    print("="*70)
    
    now = timezone.localtime(timezone.now())
    current_month = now.strftime('%Y-%m')  # مثال: 2024-10
    
    # جلب جميع الموظفين
    all_employees = Employee.objects.all()
    total_employees = all_employees.count()
    
    if total_employees == 0:
        print("⚠️ لا يوجد موظفين في النظام")
        return
    
    print(f"\n📊 عدد الموظفين: {total_employees}")
    print(f"📅 الشهر الحالي: {current_month}")
    print(f"🕐 الوقت: {now.strftime('%Y-%m-%d %H:%M')}")
    
    # إحصائيات قبل التصفير
    print("\n📈 إحصائيات قبل التصفير:")
    total_hours_before = sum(emp.total_work_hours for emp in all_employees)
    avg_hours_before = total_hours_before / total_employees if total_employees > 0 else 0
    print(f"  • إجمالي الساعات: {total_hours_before:.1f} ساعة")
    print(f"  • متوسط الساعات: {avg_hours_before:.1f} ساعة/موظف")
    
    # عرض أعلى 5 موظفين عملاً
    top_workers = sorted(all_employees, key=lambda x: x.total_work_hours, reverse=True)[:5]
    print("\n  🏆 أكثر 5 موظفين عملاً:")
    for i, emp in enumerate(top_workers, 1):
        print(f"    {i}. {emp.name}: {emp.total_work_hours:.1f} ساعة")
    
    # تصفير ساعات العمل لجميع الموظفين
    reset_count = 0
    print("\n🔄 جاري تصفير ساعات العمل...")
    
    for emp in all_employees:
        old_hours = emp.total_work_hours
        
        # تصفير الساعات
        emp.total_work_hours = 0.0
        emp.last_work_datetime = None
        emp.consecutive_rest_count = 0
        emp.save(update_fields=['total_work_hours', 'last_work_datetime', 'consecutive_rest_count'])
        
        reset_count += 1
        if old_hours > 0:
            print(f"  ✅ {emp.name}: {old_hours:.1f} → 0.0 ساعة")
    
    print(f"\n✅ تم تصفير ساعات {reset_count} موظف بنجاح!")
    
    # إنشاء سجل التصفير الشهري
    try:
        from .models import MonthlyWorkHoursReset
        
        reset_record = MonthlyWorkHoursReset.objects.create(
            year=now.year,
            month=now.month,
            total_employees=total_employees,
            total_hours_before_reset=total_hours_before,
            average_hours_before_reset=avg_hours_before
        )
        print(f"📝 تم حفظ سجل التصفير الشهري (ID: {reset_record.id})")
    except Exception as e:
        print(f"⚠️ تحذير: لم يتم حفظ سجل التصفير: {e}")
    
    # إرسال إشعارات للمشرفين/المديرين
    print("\n📢 إرسال إشعارات للإدارة...")
    
    admins_and_supervisors = User.objects.filter(
        models.Q(is_superuser=True) | 
        models.Q(supervisor_profile__is_active=True) |
        models.Q(manager_profile__is_active=True)
    ).distinct()
    
    for admin in admins_and_supervisors:
        # الحصول على معرف تليجرام
        telegram_id = None
        if hasattr(admin, 'supervisor_profile') and admin.supervisor_profile.phone:
            telegram_id = admin.supervisor_profile.phone
        elif hasattr(admin, 'manager_profile') and admin.manager_profile.phone:
            telegram_id = admin.manager_profile.phone
        
        if telegram_id:
            from .utils import send_telegram_message
            
            message = f"""
🔄 تصفير ساعات العمل الشهرية

📅 الشهر: {current_month}
🕐 الوقت: {now.strftime('%Y-%m-%d %H:%M')}

📊 الإحصائيات:
• عدد الموظفين: {total_employees}
• إجمالي الساعات: {total_hours_before:.1f} ساعة
• متوسط الساعات: {avg_hours_before:.1f} ساعة/موظف

✅ تم تصفير ساعات جميع الموظفين بنجاح!

💡 ملاحظة:
- السجلات التاريخية محفوظة في التقارير
- الموظفون يبدأون من جديد بـ 0 ساعة
- نظام العدالة يعمل من البداية

شهر جديد سعيد! 🎉
            """
            
            send_telegram_message(telegram_id, message)
            print(f"  ✅ تم إرسال إشعار إلى: {admin.username}")
    
    print("\n" + "="*70)
    print("✅ اكتملت عملية التصفير الشهرية بنجاح!")
    print("="*70 + "\n")
    
    return {
        'status': 'success',
        'month': current_month,
        'employees_reset': reset_count,
        'total_hours_before': total_hours_before,
        'average_hours_before': avg_hours_before
    }