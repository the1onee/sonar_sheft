# shifts/tasks.py
from celery import shared_task
from datetime import time
from django.utils import timezone
from .models import Shift, Sonar, Employee, EmployeeAssignment, EarlyNotification
from .utils import rotate_within_shift, check_and_send_early_notifications
from .models import SystemSettings


@shared_task
def rotate_shifts_task(rotation_hours=None):
    """
    مهمة التبديل التلقائي مع الأولويات التالية:
    1. الأولوية الأولى: التبديل في نهاية كل شفت (7:00, 15:00, 23:00) مع إشعار قبل 10 دقائق
    2. الأولوية الثانية: التبديل حسب rotation_interval_hours من آخر تبديل رسمي
    """
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
    lead_minutes = max(int(settings.early_notification_minutes or 10), 0)
    current_time = now_local.time()
    current_date = now_local.date()
    
    # تعريف أوقات نهاية الشفتات
    shift_end_times = {
        "night": time(7, 0),      # نهاية الليلي - بداية الصباحي
        "morning": time(15, 0),   # نهاية الصباحي - بداية المسائي  
        "evening": time(23, 0),   # نهاية المسائي - بداية الليلي
    }
    
    # خريطة الشفتات التالية
    next_shift_map = {
        "morning": "evening",  # بعد الصباحي يأتي المسائي
        "evening": "night",    # بعد المسائي يأتي الليلي
        "night": "morning"     # بعد الليلي يأتي الصباحي
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
    
    # 🔧 دالة لتحديد الشفت بناءً على وقت معين
    def get_shift_for_time(check_time):
        """تحديد الشفت المناسب لوقت معين"""
        for shift_name, (start, end) in shift_ranges.items():
            if start <= end:  # شفت عادي
                if start <= check_time < end:
                    return shift_name
            else:  # شفت يمر منتصف الليل
                if check_time >= start or check_time < end:
                    return shift_name
        return None
    
    # تحديد الشفت الحالي
    current_shift_name = get_shift_for_time(current_time)
    
    if not current_shift_name:
        print("❌ لا يوجد شفت نشط حاليا")
        return
    
    try:
        current_shift = Shift.objects.get(name__iexact=current_shift_name.strip())
    except Shift.DoesNotExist:
        print(f"❌ الشفت {current_shift_name} غير موجود")
        return
    
    current_tz = timezone.get_current_timezone()

    def ensure_aware(dt):
        """ضمان أن التاريخ/الوقت يحتوي على المنطقة الزمنية المستخدمة."""
        if timezone.is_aware(dt):
            return dt
        return timezone.make_aware(dt, current_tz)

    def calculate_shift_start_datetime(shift_obj):
        """إرجاع بداية الشفت الحالية لاستخدامها كمرجع للتبديل الدوري."""
        shift_start = now_local.replace(
            hour=shift_obj.start_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        if shift_obj.end_hour <= shift_obj.start_hour and now_local.hour < shift_obj.start_hour:
            shift_start -= timedelta(days=1)
        return shift_start

    shift_start = calculate_shift_start_datetime(current_shift)
    
    # الحصول على ساعات التبديل من الإعدادات
    rotation_hours = settings.get_effective_rotation_hours()
    rotation_minutes = rotation_hours * 60
    
    # ============================================
    # 🔥 الأولوية الأولى: التبديل في نهاية الشفت
    # ============================================
    # إشعار قبل 10 دقائق من نهاية الشفت (6:50, 14:50, 22:50)
    # التبديل في نهاية الشفت (7:00, 15:00, 23:00) للشفت التالي

    for shift_name, end_time in shift_end_times.items():
        # حساب وقت نهاية الشفت
        end_datetime = datetime.combine(current_date, end_time)
        if end_time.hour < 12 and current_time.hour >= 12:
            end_datetime += timedelta(days=1)
        elif end_time.hour >= 12 and current_time.hour < 12:
            end_datetime -= timedelta(days=1)

        # تحويل إلى وقت واعٍ بالمنطقة الزمنية
        end_datetime = timezone.make_aware(end_datetime, current_tz)
        
        # وقت الإشعار (قبل 10 دقائق من نهاية الشفت)
        notification_time = end_datetime - timedelta(minutes=10)
        
        # حساب الفرق بالدقائق
        time_diff = (end_datetime - now).total_seconds() / 60
        notification_diff = (notification_time - now).total_seconds() / 60
        
        # الشفت التالي
        next_shift_name = next_shift_map.get(shift_name)
        
        # حالة 1: إرسال إشعار قبل 10 دقائق من نهاية الشفت (نطاق ±2 دقيقة)
        if -2 <= notification_diff <= 2:
            # التحقق من عدم إرسال الإشعار مسبقاً
            try:
                next_shift = Shift.objects.get(name__iexact=next_shift_name)
            except Shift.DoesNotExist:
                print(f"❌ الشفت {next_shift_name} غير موجود")
                continue
            
            # وقت التبديل الرسمي (نهاية الشفت = بداية الشفت التالي)
            official_rotation_time = end_datetime
            
            # التحقق من وجود تبديل مسبق
            existing_assignment = EmployeeAssignment.objects.filter(
                assigned_at=official_rotation_time,
                shift=next_shift
            ).first()
            
            if existing_assignment:
                # التحقق من عدم إرسال إشعار مسبقاً
                recent_notification = EarlyNotification.objects.filter(
                    assignment=existing_assignment,
                    notification_type='employee',
                    notification_stage='initial',
                    sent_at__gte=now - timedelta(minutes=5)
                ).exists()
                
                if not recent_notification:
                    print(f"📢 إشعار نهاية الشفت: قبل 10 دقائق من نهاية {shift_labels.get(shift_name)} → بداية {shift_labels.get(next_shift_name)}")
                    try:
                        rotate_within_shift(
                            next_shift_name, 
                            rotation_hours, 
                            lead_time_minutes=10, 
                            next_rotation_time=official_rotation_time, 
                            is_early_notification=True
                        )
                        print(f"✅ تم إرسال إشعار نهاية الشفت للشفت {shift_labels.get(next_shift_name)}")
                        return
                    except Exception as e:
                        print(f"❌ خطأ في إرسال إشعار نهاية الشفت: {e}")
                        return
            else:
                # إنشاء التبديلات وإرسال الإشعار
                print(f"📢 إشعار نهاية الشفت: قبل 10 دقائق من نهاية {shift_labels.get(shift_name)} → بداية {shift_labels.get(next_shift_name)}")
                try:
                    rotate_within_shift(
                        next_shift_name, 
                        rotation_hours, 
                        lead_time_minutes=10, 
                        next_rotation_time=official_rotation_time, 
                        is_early_notification=True
                    )
                    print(f"✅ تم إرسال إشعار نهاية الشفت للشفت {shift_labels.get(next_shift_name)}")
                    return
                except Exception as e:
                    print(f"❌ خطأ في إرسال إشعار نهاية الشفت: {e}")
                    return
        
        # حالة 2: تنفيذ التبديل في نهاية الشفت (نطاق ±2 دقيقة)
        if -2 <= time_diff <= 2:
            # التحقق من عدم التبديل مرتين في نفس الفترة
            if settings.last_rotation_time:
                time_since_last = now - settings.last_rotation_time
                if time_since_last < timedelta(minutes=5):
                    print(f"⏸️ تم التبديل مؤخراً. تجاهل...")
                    return
            
            try:
                next_shift = Shift.objects.get(name__iexact=next_shift_name)
            except Shift.DoesNotExist:
                print(f"❌ الشفت {next_shift_name} غير موجود")
                continue
            
            # وقت التبديل الرسمي (نهاية الشفت = بداية الشفت التالي)
            official_rotation_time = end_datetime
            
            print(f"⏰ نهاية الشفت! {shift_labels.get(shift_name)} → بداية {shift_labels.get(next_shift_name)}")
            try:
                # تنفيذ التبديل للشفت التالي
                rotate_within_shift(
                    next_shift_name, 
                    rotation_hours, 
                    lead_time_minutes=0, 
                    next_rotation_time=official_rotation_time, 
                    is_early_notification=False
                )
                # تحديث last_rotation_time إلى الوقت الرسمي (نهاية الشفت)
                settings.last_rotation_time = official_rotation_time
                settings.save(update_fields=['last_rotation_time'])
                print(f"✅ تبديل نهاية الشفت: {shift_labels.get(shift_name)} → {shift_labels.get(next_shift_name)}")
                return
            except Exception as e:
                print(f"❌ خطأ في تبديل نهاية الشفت: {e}")
                return
    
    # ============================================
    # 🔥 الأولوية الثانية: التبديل حسب الإعدادات
    # ============================================
    # التبديل حسب rotation_interval_hours من آخر تبديل رسمي
    
    if not settings.last_rotation_time:
        # أول مرة - نحسب التبديل الأول من بداية الشفت
        print(f"🆕 أول تبديل في النظام - حساب التبديل الأول من بداية الشفت {shift_labels.get(current_shift_name)}")
        
        # حساب وقت التبديل الأول من بداية الشفت
        shift_start = calculate_shift_start_datetime(current_shift)
        
        hours_since_start = (now_local - shift_start).total_seconds() / 3600
        rotation_index = int(hours_since_start // rotation_hours)
        first_rotation_time = shift_start + timedelta(hours=rotation_index * rotation_hours)
        
        if first_rotation_time < now_local:
            first_rotation_time += timedelta(hours=rotation_hours)
        
        first_rotation_time_aware = timezone.make_aware(first_rotation_time)
        time_until_first = (first_rotation_time_aware - now).total_seconds() / 60
        
        if time_until_first > 0:
            # التبديل في المستقبل - إنشاء التبديلات فقط
            print(f"⏳ التبديل الأول في المستقبل ({int(time_until_first)} دقيقة)")
            try:
                rotate_within_shift(
                    current_shift_name, 
                    rotation_hours, 
                    lead_time_minutes=0, 
                    next_rotation_time=first_rotation_time_aware, 
                    is_early_notification=True
                )
                settings.last_rotation_time = first_rotation_time_aware - timedelta(hours=rotation_hours)
                settings.save(update_fields=['last_rotation_time'])
                print(f"✅ تم إنشاء التبديلات للفترة {first_rotation_time.strftime('%H:%M')}")
            except Exception as e:
                print(f"❌ خطأ في إنشاء التبديلات الأولية: {e}")
        else:
            # التبديل الآن - تنفيذ فوراً
            print(f"🔄 التبديل الأول الآن")
            try:
                rotate_within_shift(
                    current_shift_name, 
                    rotation_hours, 
                    lead_time_minutes=0, 
                    next_rotation_time=first_rotation_time_aware, 
                    is_early_notification=False
                )
                settings.last_rotation_time = first_rotation_time_aware
                settings.save(update_fields=['last_rotation_time'])
                print(f"✅ تم التبديل الأولي بنجاح")
            except Exception as e:
                print(f"❌ خطأ في التبديل الأولي: {e}")
        return
    
    # =========================
    # ⛔ أولوية ثانية: منع التبديل الداخلي في آخر 59 دقيقة من الشفت
    # =========================
    shift_end_time = shift_end_times[current_shift_name]
    shift_end_dt = shift_start.replace(
        hour=shift_end_time.hour,
        minute=shift_end_time.minute,
        second=0,
        microsecond=0
    )
    if shift_end_time.hour <= current_shift.start_hour:
        shift_end_dt += timedelta(days=1)
    minutes_to_shift_end = (shift_end_dt - now_local).total_seconds() / 60
    lock_window_minutes = 59
    if 0 <= minutes_to_shift_end <= lock_window_minutes:
        print(
            f"🛑 تم إيقاف التبديل الدوري لأن الشفت ينتهي بعد "
            f"{int(minutes_to_shift_end)} دقيقة (الأولوية للأولوية الأولى فقط)"
        )
        return

    # حساب وقت التبديل القادم من آخر تبديل رسمي
    required_interval = timedelta(hours=rotation_hours)
    if required_interval.total_seconds() <= 0:
        print("❌ فترة التبديل غير صحيحة (<=0)")
        return

    shift_start_aware = ensure_aware(shift_start)
    last_rotation_aware = ensure_aware(settings.last_rotation_time)
    now_local_aware = ensure_aware(now_local)

    interval_seconds = required_interval.total_seconds()
    elapsed_since_start = max((now_local_aware - shift_start_aware).total_seconds(), 0)
    slots_elapsed = int(elapsed_since_start // interval_seconds)
    anchored_last_rotation = shift_start_aware + (required_interval * slots_elapsed)
    if anchored_last_rotation > now_local_aware:
        anchored_last_rotation -= required_interval

    alignment_threshold = timedelta(minutes=1)
    if abs((last_rotation_aware - anchored_last_rotation).total_seconds()) >= alignment_threshold.total_seconds():
        print(
            f"🔧 إعادة محاذاة سجل التبديل الدوري إلى {anchored_last_rotation.strftime('%H:%M')} "
            "لضمان البدء من بداية الشفت"
        )
        settings.last_rotation_time = anchored_last_rotation
        settings.save(update_fields=['last_rotation_time'])
        last_rotation_aware = anchored_last_rotation

    time_since_last = now - settings.last_rotation_time
    catchup_rotations = 0
    max_catchup_rotations = 6  # حماية من عدد كبير من التبديلات المتأخرة

    while time_since_last >= required_interval and catchup_rotations < max_catchup_rotations:
        next_rotation_time = settings.last_rotation_time + required_interval
        next_rotation_time_local = timezone.localtime(next_rotation_time)
        hours_since = time_since_last.total_seconds() / 3600
        
        # 🔧 تحديد الشفت الصحيح بناءً على وقت التبديل (وليس الوقت الحالي)
        target_shift_name = get_shift_for_time(next_rotation_time_local.time())
        if not target_shift_name:
            target_shift_name = current_shift_name
        
        print(
            f"⏱️ مر {hours_since:.1f} ساعة من آخر تبديل "
            f"(المطلوب: {rotation_hours} ساعة) - تنفيذ تبديل تعويضي #{catchup_rotations + 1} للشفت {shift_labels.get(target_shift_name)}"
        )
        try:
            rotate_within_shift(
                target_shift_name,  # استخدام الشفت الصحيح
                rotation_hours,
                lead_time_minutes=0,
                next_rotation_time=next_rotation_time,
                is_early_notification=False
            )
            settings.last_rotation_time = next_rotation_time
            settings.save(update_fields=['last_rotation_time'])
            print(f"✅ تبديل دوري (تعويضي) في {next_rotation_time_local.strftime('%H:%M')} - شفت {shift_labels.get(target_shift_name)}")
            catchup_rotations += 1
            time_since_last = now - settings.last_rotation_time
        except Exception as e:
            print(f"❌ خطأ في التبديل الدوري: {e}")
            return

    if catchup_rotations > 0:
        if time_since_last >= required_interval:
            total_delay_hours = time_since_last.total_seconds() / 3600
            print(
                f"⚠️ بقي {total_delay_hours:.1f} ساعة متأخرة بعد {catchup_rotations} تبديلات."
                " سيُستكمل التعويض في الدورة القادمة."
            )
        else:
            print(f"✅ تمت معالجة كل التبديلات المتأخرة ({catchup_rotations})")
        return

    next_rotation_time = settings.last_rotation_time + required_interval
    next_rotation_time_local = timezone.localtime(next_rotation_time)
    
    # حساب الوقت المتبقي
    time_until_next = next_rotation_time - now
    minutes_until_next = time_until_next.total_seconds() / 60
    
    # التحقق إذا حان وقت إرسال الإشعار المبكر
    notification_time = next_rotation_time - timedelta(minutes=lead_minutes)
    time_until_notification = notification_time - now
    minutes_until_notification = time_until_notification.total_seconds() / 60
    
    # نطاق الإشعار: ±2 دقيقة
    notification_window = 2
    
    if -notification_window <= minutes_until_notification <= notification_window:
        # 🔧 تحديد الشفت الصحيح بناءً على وقت التبديل (وليس الوقت الحالي)
        target_shift_name = get_shift_for_time(next_rotation_time_local.time())
        if not target_shift_name:
            target_shift_name = current_shift_name
        
        # التحقق من عدم إرسال الإشعار مسبقاً
        existing_assignment = EmployeeAssignment.objects.filter(
            assigned_at=next_rotation_time,
            shift__name=target_shift_name  # استخدام الشفت الصحيح
        ).first()
        
        if existing_assignment:
            recent_notification = EarlyNotification.objects.filter(
                assignment=existing_assignment,
                notification_type='employee',
                notification_stage='initial',
                sent_at__gte=now - timedelta(minutes=5)
            ).exists()
            
            if not recent_notification:
                print(f"📢 حان وقت إرسال الإشعار المبكر! التبديل القادم في {next_rotation_time_local.strftime('%H:%M')} - شفت {shift_labels.get(target_shift_name)}")
                try:
                    rotate_within_shift(
                        target_shift_name,  # استخدام الشفت الصحيح
                        rotation_hours, 
                        lead_time_minutes=lead_minutes, 
                        next_rotation_time=next_rotation_time, 
                        is_early_notification=True
                    )
                    print(f"✅ تم إرسال الإشعار المبكر بنجاح - شفت {shift_labels.get(target_shift_name)}")
                    return
                except Exception as e:
                    print(f"❌ خطأ في إرسال الإشعار المبكر: {e}")
                    return
        else:
            # إنشاء التبديلات وإرسال الإشعار
            print(f"📢 حان وقت إرسال الإشعار المبكر! التبديل القادم في {next_rotation_time_local.strftime('%H:%M')} - شفت {shift_labels.get(target_shift_name)}")
            try:
                rotate_within_shift(
                    target_shift_name,  # استخدام الشفت الصحيح
                    rotation_hours, 
                    lead_time_minutes=lead_minutes, 
                    next_rotation_time=next_rotation_time, 
                    is_early_notification=True
                )
                print(f"✅ تم إرسال الإشعار المبكر بنجاح - شفت {shift_labels.get(target_shift_name)}")
                return
            except Exception as e:
                print(f"❌ خطأ في إرسال الإشعار المبكر: {e}")
                return
    else:
        # لم يحن وقت التبديل أو الإشعار بعد
        remaining_time = required_interval - time_since_last
        minutes_remaining = remaining_time.total_seconds() / 60
        print(f"⏳ لم يحن وقت التبديل بعد | متبقي: {minutes_remaining:.1f} دقيقة | شفت: {shift_labels.get(current_shift_name)}")
        if minutes_until_notification > 0:
            print(f"   📢 الإشعار سيُرسل في: {timezone.localtime(notification_time).strftime('%H:%M')} (متبقي: {minutes_until_notification:.1f} دقيقة)")


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
