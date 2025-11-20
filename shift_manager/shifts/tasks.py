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
    
    # حساب وقت التبديل القادم
    if settings.last_rotation_time:
        # حساب وقت التبديل القادم بناءً على آخر تبديل + فترة التبديل
        next_rotation_time = settings.last_rotation_time + timedelta(hours=rotation_hours)
        next_rotation_time_local = timezone.localtime(next_rotation_time)
        
        # حساب الوقت المتبقي حتى التبديل القادم
        time_until_next = next_rotation_time - now
        minutes_until_next = time_until_next.total_seconds() / 60
        
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
            elif end_time.hour >= 12 and current_time.hour < 12:
                current_datetime -= timedelta(days=1)
            
            time_diff = (end_datetime - current_datetime).total_seconds() / 60
            
            # إذا كنا في آخر 15 دقيقة من الشيفت أو مرت 5 دقائق من بدايته
            if -5 <= time_diff <= 15:
                is_shift_end = True
                shift_to_rotate = shift_name
                print(f"⏰ نهاية الشيفت! {shift_labels.get(shift_name)} | الوقت المتبقي: {time_diff:.1f} دقيقة | تبديل مباشر")
                
                # التحقق من عدم التبديل مرتين في نفس الفترة (كل 15 دقيقة على الأقل)
                time_since_last = now - settings.last_rotation_time
                if time_since_last < timedelta(minutes=15):
                    minutes_since = time_since_last.total_seconds() / 60
                    print(f"⏸️ تم التبديل مؤخراً ({minutes_since:.1f} دقيقة مضت). تجاهل...")
                    return
                
                # تنفيذ التبديل فوراً عند نهاية الشيفت
                try:
                    rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=0, next_rotation_time=now)
                    settings.update_last_rotation_time()
                    print(f"✅ تبديل نهاية الشيفت: {shift_labels.get(shift_name)} → الشيفت التالي")
                    return
                except Exception as e:
                    print(f"❌ خطأ في تبديل نهاية الشيفت: {e}")
                    return
        
        # 🔥 الأولوية الثانية: التحقق إذا حان وقت التبديل (مرت فترة التبديل)
        required_interval = timedelta(hours=rotation_hours)
        time_since_last = now - settings.last_rotation_time
        
        if time_since_last >= required_interval:
            # حان وقت التبديل حسب الإعدادات
            hours_since = time_since_last.total_seconds() / 3600
            print(f"⏱️ مر {hours_since:.1f} ساعة من آخر تبديل (المطلوب: {rotation_hours} ساعة)")
            
            try:
                # استخدام وقت التبديل المحسوب (وليس الوقت الحالي)
                rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=0, next_rotation_time=next_rotation_time)
                settings.update_last_rotation_time()
                print(f"✅ تبديل دوري: كل {rotation_hours} ساعة في شفت {shift_labels.get(current_shift_name)}")
                return
            except Exception as e:
                print(f"❌ خطأ في التبديل الدوري: {e}")
                return
        else:
            # 🔔 الأولوية الثالثة: التحقق إذا حان وقت إرسال الإشعار المبكر (قبل 30 دقيقة من التبديل)
            notification_time = next_rotation_time - timedelta(minutes=lead_minutes)
            time_until_notification = notification_time - now
            minutes_until_notification = time_until_notification.total_seconds() / 60
            
            # تحديد الشفت المستهدف للإشعار
            # 🎯 أولوية خاصة: إذا كان الوقت في نطاق 7-15 (صباحي)، نرسل للشفت الحالي
            # 🎯 لباقي الأوقات: إذا كان قبل 30 دقيقة من نهاية الشفت، نرسل للشفت التالي
            target_shift_name = current_shift_name
            target_rotation_time = next_rotation_time
            
            # التحقق إذا كنا قبل 30 دقيقة من نهاية الشفت
            is_before_shift_end = False
            next_shift_name = None
            
            # خريطة الشفتات التالية
            next_shift_map = {
                "morning": "evening",  # بعد الصباحي يأتي المسائي
                "evening": "night",    # بعد المسائي يأتي الليلي
                "night": "morning"     # بعد الليلي يأتي الصباحي
            }
            
            for shift_name, end_time in shift_end_times.items():
                # حساب الفرق بالدقائق من وقت نهاية الشيفت
                current_datetime = datetime.combine(now_local.date(), current_time)
                end_datetime = datetime.combine(now_local.date(), end_time)
                
                # معالجة حالة منتصف الليل
                if end_time.hour < 12 and current_time.hour >= 12:
                    end_datetime += timedelta(days=1)
                elif end_time.hour >= 12 and current_time.hour < 12:
                    current_datetime -= timedelta(days=1)
                
                time_diff = (end_datetime - current_datetime).total_seconds() / 60
                
                # إذا كنا قبل 30 دقيقة (±5 دقائق) من نهاية الشفت
                if 25 <= time_diff <= 35:
                    is_before_shift_end = True
                    next_shift_name = next_shift_map.get(shift_name)
                    
                    # 🎯 أولوية خاصة لكل شفت: إذا كان الوقت في نطاق الشفت وليس قبل 30 دقيقة من النهاية
                    # 🎯 لباقي الأوقات أو قبل 30 دقيقة من النهاية: نرسل للشفت التالي
                    is_in_shift_priority = False
                    
                    # التحقق من أولوية الصباحي (7-14:30)
                    if current_shift_name == "morning" and time(7, 0) <= current_time < time(14, 30):
                        is_in_shift_priority = True
                    
                    # التحقق من أولوية المسائي (15-22:30)
                    elif current_shift_name == "evening" and time(15, 0) <= current_time < time(22, 30):
                        is_in_shift_priority = True
                    
                    # التحقق من أولوية الليلي (23-6:30)
                    elif current_shift_name == "night":
                        # الشفت الليلي يمر منتصف الليل
                        if current_time >= time(23, 0) or current_time < time(6, 30):
                            is_in_shift_priority = True
                    
                    if is_in_shift_priority:
                        # في نطاق الشفت (قبل 30 دقيقة من النهاية) - إرسال للشفت الحالي
                        target_shift_name = current_shift_name
                        target_rotation_time = next_rotation_time
                        shift_range_label = ""
                        if current_shift_name == "morning":
                            shift_range_label = "7-14:30"
                        elif current_shift_name == "evening":
                            shift_range_label = "15-22:30"
                        elif current_shift_name == "night":
                            shift_range_label = "23-6:30"
                        print(f"📢 أولوية خاصة للشفت {shift_labels.get(current_shift_name)} ({shift_range_label}): إرسال إشعار للشفت الحالي ({shift_labels.get(current_shift_name)})")
                    else:
                        # لباقي الأوقات أو قبل 30 دقيقة من النهاية: نرسل للشفت التالي
                        if next_shift_name:
                            target_shift_name = next_shift_name
                            # حساب وقت بداية الشفت التالي (نهاية الشفت الحالي = بداية الشفت التالي)
                            next_shift_start_datetime = end_datetime
                            
                            # حساب وقت التبديل في الشفت التالي (بداية الشفت)
                            target_rotation_time = timezone.make_aware(next_shift_start_datetime)
                            target_rotation_time_local = timezone.localtime(target_rotation_time)
                            print(f"📢 قبل 30 دقيقة من نهاية الشفت ({shift_labels.get(shift_name)}): إرسال إشعار للشفت التالي ({shift_labels.get(next_shift_name)}) في {target_rotation_time_local.strftime('%H:%M')}")
                    break
            
            # إذا كان الوقت الحالي في نطاق ±5 دقائق من وقت الإشعار
            if -5 <= minutes_until_notification <= 5 or is_before_shift_end:
                # التحقق من عدم إرسال الإشعار مسبقاً
                from .models import EmployeeAssignment, EarlyNotification
                existing_assignment = EmployeeAssignment.objects.filter(
                    assigned_at=target_rotation_time,
                    shift__name=target_shift_name
                ).first()
                
                if existing_assignment:
                    # التحقق من وجود إشعار مبكر مسبق
                    early_notification_exists = EarlyNotification.objects.filter(
                        assignment=existing_assignment,
                        notification_type='employee',
                        notification_stage='early'
                    ).exists()
                    
                    if not early_notification_exists:
                        print(f"📢 حان وقت إرسال الإشعار المبكر! التبديل القادم في {timezone.localtime(target_rotation_time).strftime('%H:%M')} للشفت {shift_labels.get(target_shift_name)}")
                        try:
                            # إرسال الإشعار قبل 30 دقيقة من وقت التبديل الفعلي (بدون تحديث last_rotation_time)
                            rotate_within_shift(target_shift_name, rotation_hours, lead_time_minutes=lead_minutes, next_rotation_time=target_rotation_time, is_early_notification=True)
                            print(f"✅ تم إرسال الإشعار المبكر بنجاح للشفت {shift_labels.get(target_shift_name)}")
                            return
                        except Exception as e:
                            print(f"❌ خطأ في إرسال الإشعار المبكر: {e}")
                            return
                    else:
                        print(f"⏸️ تم إرسال الإشعار المبكر مسبقاً")
                else:
                    # إنشاء التبديلات وإرسال الإشعار
                    print(f"📢 حان وقت إرسال الإشعار المبكر! التبديل القادم في {timezone.localtime(target_rotation_time).strftime('%H:%M')} للشفت {shift_labels.get(target_shift_name)}")
                    try:
                        # إرسال الإشعار قبل 30 دقيقة من وقت التبديل الفعلي (بدون تحديث last_rotation_time)
                        rotate_within_shift(target_shift_name, rotation_hours, lead_time_minutes=lead_minutes, next_rotation_time=target_rotation_time, is_early_notification=True)
                        print(f"✅ تم إرسال الإشعار المبكر بنجاح للشفت {shift_labels.get(target_shift_name)}")
                        return
                    except Exception as e:
                        print(f"❌ خطأ في إرسال الإشعار المبكر: {e}")
                        return
            else:
                # لم يحن وقت التبديل أو الإشعار بعد
                remaining_time = required_interval - time_since_last
                minutes_remaining = remaining_time.total_seconds() / 60
                print(f"⏳ لم يحن وقت التبديل بعد | متبقي: {minutes_remaining:.1f} دقيقة | شفت: {shift_labels.get(current_shift_name)}")
                print(f"   📢 الإشعار سيُرسل في: {timezone.localtime(notification_time).strftime('%H:%M')} (متبقي: {minutes_until_notification:.1f} دقيقة)")
    else:
        # أول مرة يتم تشغيل النظام - نحسب التبديل الأول من بداية الشفت
        print(f"🆕 أول تبديل في النظام - حساب التبديل الأول من بداية الشفت {shift_labels.get(current_shift_name)}")
        
        # الحصول على الشفت الحالي من قاعدة البيانات
        try:
            from .models import Shift
            shift = Shift.objects.get(name__iexact=current_shift_name.strip())
        except Shift.DoesNotExist:
            print(f"❌ الشفت {current_shift_name} غير موجود")
            return
        
        # حساب وقت التبديل الأول من بداية الشفت
        shift_start = now_local.replace(hour=shift.start_hour, minute=0, second=0, microsecond=0)
        if shift.end_hour <= shift.start_hour and now_local.hour < shift.start_hour:
            # شفت ليلي - قد يكون shift_start في اليوم السابق
            shift_start -= timedelta(days=1)
        
        # حساب عدد فترات التبديل منذ بداية الشفت
        hours_since_start = (now_local - shift_start).total_seconds() / 3600
        rotation_index = int(hours_since_start // rotation_hours)
        first_rotation_time = shift_start + timedelta(hours=rotation_index * rotation_hours)
        
        # إذا كان وقت التبديل المحسوب في الماضي، نأخذ التبديل التالي
        if first_rotation_time < now_local:
            first_rotation_time += timedelta(hours=rotation_hours)
        
        first_rotation_time_aware = timezone.make_aware(first_rotation_time)
        
        print(f"⏰ وقت التبديل الأول المحسوب: {first_rotation_time.strftime('%H:%M')} (من بداية الشفت {shift.start_hour}:00)")
        
        # التحقق إذا كان وقت التبديل في المستقبل
        time_until_first = (first_rotation_time_aware - now).total_seconds() / 60
        
        if time_until_first > 0:
            # التبديل في المستقبل - ننشئ التبديلات فقط (بدون تحديث last_rotation_time)
            print(f"⏳ التبديل الأول في المستقبل ({int(time_until_first)} دقيقة) - إنشاء التبديلات فقط")
            try:
                # نستخدم is_early_notification=True لتجنب تحديث last_rotation_time
                rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=0, next_rotation_time=first_rotation_time_aware, is_early_notification=True)
                # تعيين last_rotation_time إلى وقت قبل التبديل الأول بحيث يحسب التبديل القادم بشكل صحيح
                # نستخدم وقت قبل التبديل الأول بفترة التبديل
                settings.last_rotation_time = first_rotation_time_aware - timedelta(hours=rotation_hours)
                settings.save(update_fields=['last_rotation_time'])
                print(f"✅ تم إنشاء التبديلات للفترة {first_rotation_time.strftime('%H:%M')} - سيحدث التبديل الفعلي عند حلول الوقت")
            except Exception as e:
                print(f"❌ خطأ في إنشاء التبديلات الأولية: {e}")
        else:
            # التبديل الآن أو في الماضي - ننفذ التبديل فوراً
            print(f"🔄 التبديل الأول الآن - تنفيذ التبديل فوراً")
            try:
                rotate_within_shift(current_shift_name, rotation_hours, lead_time_minutes=0, next_rotation_time=first_rotation_time_aware)
                settings.update_last_rotation_time()
                print(f"✅ تم التبديل الأولي بنجاح - التبديل القادم في {first_rotation_time.strftime('%H:%M')}")
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