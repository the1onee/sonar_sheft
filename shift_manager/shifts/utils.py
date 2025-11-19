import random
import requests
import os
from datetime import time, timedelta
from dotenv import load_dotenv

from django.utils import timezone
from django.db import models
from .models import Shift, Sonar, Employee, EmployeeAssignment, WeeklyShiftAssignment, SystemSettings, EarlyNotification
from django.contrib.auth.models import User

# تحميل ملف .env
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

# 🔑 رمز البوت الخاص بتطبيق تليغرام (Telegram Bot Token)
# ⚠️ يجب إضافة TELEGRAM_BOT_TOKEN في ملف .env
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    print("⚠️ تحذير: TELEGRAM_BOT_TOKEN غير موجود في متغيرات البيئة!")
    print("   الإشعارات عبر Telegram لن تعمل حتى يتم إضافة Token في ملف .env")


# 📨 دالة لإرسال رسالة إلى موظف عبر تليغرام
def send_telegram_message(chat_id, text):
    # التأكد أن الموظف لديه chat_id صالح
    if not chat_id:
        print("❌ الموظف لا يملك chat_id")
        return

    # عنوان API الخاص بتليغرام لإرسال الرسائل
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        # إرسال الطلب إلى خوادم تليغرام
        response = requests.post(url, data=payload)
        print(f"تم الإرسال للـ chat_id {chat_id}: {response.status_code}")
    except Exception as e:
        # في حال فشل الإرسال
        print(f"❌ خطأ في إرسال التليغرام: {e}")


def check_and_send_early_notifications():
    """
    فحص التبديلات القادمة وإرسال إشعار نهائي وقت التبديل الرسمي.
    يتم تجهيز الموظف قبل الموعد عبر التدوير المبكر، وهنا نرسل فقط التذكير النهائي.
    """
    settings = SystemSettings.get_current_settings()

    if not settings.is_rotation_active:
        print("🔕 التبديل التلقائي معطل - لن يتم إرسال إشعارات")
        return

    now = timezone.localtime(timezone.now())
    rotation_hours = settings.get_effective_rotation_hours()
    lead_minutes = max(int(settings.early_notification_minutes or 30), 0)

    notifications_sent = 0
    notifications_window_margin = 2  # دقائق مرونة حول الوقت الرسمي

    admins_and_supervisors = User.objects.filter(
        models.Q(is_superuser=True) | models.Q(supervisor_profile__is_active=True)
    ).distinct()

    upcoming_assignments = EmployeeAssignment.objects.filter(
        is_standby=False,
        assigned_at__gte=now - timedelta(hours=rotation_hours),
        assigned_at__lte=now + timedelta(minutes=notifications_window_margin)
    ).select_related('employee', 'sonar', 'shift')

    if not upcoming_assignments.exists():
        print("⏰ لا توجد تبديلات تحتاج إشعاراً نهائياً الآن")
        return

    for assignment in upcoming_assignments:
        if not assignment.sonar:
            continue

        work_hours = assignment.work_duration_hours or rotation_hours
        assignment_end = assignment.assigned_at + timedelta(hours=work_hours)
        minutes_until_start = int((assignment.assigned_at - now).total_seconds() / 60)

        if abs(minutes_until_start) > notifications_window_margin:
            continue

        admin_notification_exists = EarlyNotification.objects.filter(
            assignment=assignment,
            notification_type='admin',
            notification_stage='final'
        ).exists()

        employee_notification_exists = EarlyNotification.objects.filter(
            assignment=assignment,
            notification_type='employee',
            notification_stage='final'
        ).exists()

        period_label = f"{assignment.assigned_at.strftime('%H:%M')} - {assignment_end.strftime('%H:%M')}"

        if not admin_notification_exists:
            admin_message = (
                "🔔 وقت التبديل الرسمي الآن!\n\n"
                f"👤 الموظف: {assignment.employee.name}\n"
                f"📡 السونار: {assignment.sonar.name}\n"
                f"🕒 الفترة الرسمية: {period_label}\n"
                f"⏳ تم تجهيز التبديل قبل {lead_minutes} دقيقة - هذا تذكير نهائي للمتابعة."
            )

            for admin in admins_and_supervisors:
                if hasattr(admin, 'supervisor_profile') and admin.supervisor_profile.phone:
                    send_telegram_message(admin.supervisor_profile.phone, admin_message)
                elif admin.is_superuser:
                    pass

            EarlyNotification.objects.create(
                assignment=assignment,
                notification_type='admin',
                notification_stage='final',
                minutes_before=0
            )
            notifications_sent += 1
            print(f"  ✅ إشعار نهائي للإدارة: {assignment.employee.name} ({period_label})")

        if assignment.employee.telegram_id and not employee_notification_exists:
            employee_message = (
                "🔔 حان وقت التبديل الرسمي الآن!\n\n"
                f"{assignment.employee.name}،\n\n"
                f"📡 السونار: {assignment.sonar.name}\n"
                f"🕒 الفترة الرسمية: {period_label}\n\n"
                "✅ تم تجهيزك مسبقاً لتعرف مكانك. يرجى التوجه الآن والبدء في التبديل."
            )

            send_telegram_message(assignment.employee.telegram_id, employee_message)

            EarlyNotification.objects.create(
                assignment=assignment,
                notification_type='employee',
                notification_stage='final',
                minutes_before=0
            )
            notifications_sent += 1
            print(f"  ✅ إشعار نهائي للموظف: {assignment.employee.name} ({period_label})")

    if notifications_sent > 0:
        print(f"📢 تم إرسال {notifications_sent} إشعار نهائي بنجاح")
    else:
        print("⏰ لا توجد تبديلات تحتاج إشعاراً نهائياً ضمن النافذة الحالية")
# 🔁 دالة تدوير الموظفين داخل الشفت (أي تبديل مواقعهم أو السونارات)
def rotate_within_shift(shift_name, rotation_hours=None, lead_time_minutes=0):
    """
    تقوم هذه الدالة بتوزيع الموظفين على السونارات بشكل ذكي حسب سعة كل سونار
    مع إمكانية تجهيز التبديل قبل الوقت الرسمي بدقائق محددة.
    """
    print(f"🔁 بدء تدوير الشفت: {shift_name} (تجهيز مبكر: {lead_time_minutes} دقيقة)")

    # الحصول على إعدادات النظام
    settings = SystemSettings.get_current_settings()

    # استخدام الإعدادات المحفوظة إذا لم يتم تحديد rotation_hours
    if rotation_hours is None:
        rotation_hours = settings.get_effective_rotation_hours()
        print(f"📊 استخدام فترة التبديل من الإعدادات: {rotation_hours} ساعة")
    else:
        print(f"📊 استخدام فترة التبديل المحددة: {rotation_hours} ساعة")

    # ❌ رفض التبديلات السابقة غير المؤكدة قبل البدء بالتبديل الجديد
    print("\n🔍 فحص التبديلات السابقة غير المؤكدة...")
    rejected_count = cancel_expired_confirmations()
    if rejected_count > 0:
        print(f"❌ تم رفض {rejected_count} تبديل غير مؤكد من الفترة السابقة\n")

    # استخدام الوقت المحلي (Asia/Baghdad) مع مراعاة التجهيز المبكر
    lead_time_minutes = max(lead_time_minutes or 0, 0)
    lead_time_delta = timedelta(minutes=lead_time_minutes)
    now_actual = timezone.localtime(timezone.now())
    now = now_actual + lead_time_delta

    # 🕒 الحصول على الشفت الحالي من قاعدة البيانات
    try:
        shift = Shift.objects.get(name__iexact=shift_name.strip())
    except Shift.DoesNotExist:
        print(f"❌ الشفت {shift_name} غير موجود")
        return

    # تحديد بداية ونهاية الشفت بالساعة
    shift_start = now.replace(hour=shift.start_hour, minute=0, second=0, microsecond=0)
    shift_end = now.replace(hour=shift.end_hour, minute=0, second=0, microsecond=0)

    # في حال الشفت الليلي (ينتهي بعد منتصف الليل)
    if shift.end_hour <= shift.start_hour:
        shift_end += timedelta(days=1)

    # 🔍 جلب جميع السونارات (Sonar) النشطة فقط
    active_sonars = list(Sonar.objects.filter(active=True))
    if not active_sonars:
        print(f"❌ لا يوجد سونارات فعالة للشفت {shift.name}")
        return

    # 🔎 البحث عن توزيع الأسبوع الحالي للشفت (WeeklyShiftAssignment)
    assignments = WeeklyShiftAssignment.objects.filter(
        shift=shift,
        week_start_date__lte=now.date(),
        week_end_date__gte=now.date()
    )

    # 🧑‍💼 جمع جميع الموظفين الذين يعملون في هذا الشفت وغير مجازين
    employees = []
    for assignment in assignments:
        employees.extend([emp for emp in assignment.employees.all() if not emp.is_on_leave])

    if not employees:
        print(f"⚠️ لا يوجد موظفين متاحين للشفت {shift.name}")
        return

    # حساب كم مضى من الساعات منذ بداية الشفت لتحديد المجموعة الحالية
    hours_since_start = (now - shift_start).total_seconds() / 3600
    rotation_index = int(hours_since_start // rotation_hours)

    # حساب وقت بداية ونهاية الفترة الحالية للدوران
    current_rotation_start = shift_start + timedelta(hours=rotation_index * rotation_hours)
    current_rotation_end = min(current_rotation_start + timedelta(hours=rotation_hours), shift_end)
    display_start_str = current_rotation_start.strftime('%H:%M')
    display_end_str = current_rotation_end.strftime('%H:%M')
    official_window_label = f"{display_start_str} - {display_end_str}"

    # 🎯 نظام التبديل العادل - ترتيب الموظفين حسب الأولوية
    print(f"\n📊 حساب أولويات الموظفين للتبديل العادل ({official_window_label})...")
    
    # حساب متوسط ساعات العمل لجميع الموظفين
    total_work_hours = sum(emp.total_work_hours for emp in employees)
    avg_work_hours = total_work_hours / len(employees) if len(employees) > 0 else 0.0
    print(f"  📊 متوسط ساعات العمل للجميع: {avg_work_hours:.1f} ساعة")
    
    # حساب نقاط الأولوية لكل موظف
    employee_priorities = []
    for emp in employees:
        priority_score = emp.get_priority_score(avg_work_hours)
        diff_from_avg = emp.total_work_hours - avg_work_hours
        employee_priorities.append((emp, priority_score))
        
        # رمز الحالة
        if diff_from_avg < -1:
            status = "🔺 يحتاج عمل"
        elif diff_from_avg > 1:
            status = "🔻 يحتاج راحة"
        else:
            status = "⚖️ متوازن"
        
        print(f"  📌 {emp.name}: نقاط={priority_score:.1f} | عمل={emp.total_work_hours:.1f}س | فرق عن المتوسط={diff_from_avg:+.1f}س | {status}")
    
    # ترتيب الموظفين حسب الأولوية (الأقل نقاطاً = الأعلى أولوية للعمل)
    employee_priorities.sort(key=lambda x: x[1])
    sorted_employees = [emp for emp, score in employee_priorities]
    
    print("\n🔄 ترتيب الأولوية للعمل (من الأعلى للأقل):")
    for i, (emp, score) in enumerate(employee_priorities[:10], 1):  # عرض أول 10 فقط
        diff = emp.total_work_hours - avg_work_hours
        print(f"  {i}. {emp.name} (نقاط: {score:.1f} | عمل: {emp.total_work_hours:.1f}س | فرق: {diff:+.1f}س)")
    
    # حساب إجمالي المقاعد المتاحة في جميع السونارات
    total_available_slots = sum(sonar.max_employees for sonar in active_sonars)
    
    print(f"\n📍 إجمالي المقاعد المتاحة: {total_available_slots}")
    print(f"📍 إجمالي الموظفين: {len(sorted_employees)}")
    
    # تقسيم الموظفين إلى: عاملين + احتياط
    working_employees = sorted_employees[:total_available_slots]
    standby_employees = sorted_employees[total_available_slots:]
    
    print(f"\n✅ الموظفين العاملين: {len(working_employees)}")
    print(f"💤 الموظفين في الاحتياط: {len(standby_employees)}")
    
    # 📊 قاموس لتتبع عدد الموظفين المعينين لكل سونار
    sonar_assignment_count = {sonar.id: 0 for sonar in active_sonars}
    
    # خلط السونارات لتوزيع عشوائي عادل
    shuffled_sonars = active_sonars.copy()
    random.shuffle(shuffled_sonars)
    
    # 📝 قوائم لتتبع التوزيع
    work_assignments = []  # (موظف, سونار)
    standby_assignments = []  # موظف
    
    # 🎯 المرحلة الأولى: توزيع الموظفين العاملين على السونارات
    print("\n📍 المرحلة 1: توزيع الموظفين على السونارات حسب الأولوية...")
    
    employee_index = 0
    for sonar in shuffled_sonars:
        for slot in range(sonar.max_employees):
            if employee_index >= len(working_employees):
                break
            
            emp = working_employees[employee_index]
            
            # 🧾 حفظ التعيين الجديد في قاعدة البيانات
            assignment = EmployeeAssignment.objects.create(
                employee=emp,
                sonar=sonar,
                shift=shift,
                assigned_at=current_rotation_start,
                rotation_number=0,
                is_standby=False,  # الموظف يعمل
                work_duration_hours=rotation_hours
            )
            
            # تحديث إحصائيات الموظف
            emp.total_work_hours += rotation_hours
            emp.last_work_datetime = current_rotation_start
            emp.consecutive_rest_count = 0  # إعادة تعيين عداد الراحة
            emp.save()
            
            sonar_assignment_count[sonar.id] += 1
            work_assignments.append((emp, sonar))
            employee_index += 1
            
            print(f"  ✅ {emp.name} → {sonar.name} ({sonar_assignment_count[sonar.id]}/{sonar.max_employees})")
    
    # 🎯 المرحلة الثانية: تسجيل الموظفين في الاحتياط
    if standby_employees:
        print(f"\n📍 المرحلة 2: تسجيل {len(standby_employees)} موظف في حالة احتياط...")
        
        for emp in standby_employees:
            # 🧾 حفظ التعيين كاحتياط (بدون سونار)
            assignment = EmployeeAssignment.objects.create(
                employee=emp,
                sonar=None,  # لا يوجد سونار للاحتياط
                shift=shift,
                assigned_at=current_rotation_start,
                rotation_number=0,
                is_standby=True,  # الموظف في احتياط
                work_duration_hours=0.0  # لا يعمل
            )
            
            # تحديث عداد الراحة المتتالية
            emp.consecutive_rest_count += 1
            emp.save()
            
            standby_assignments.append(emp)
            print(f"  💤 {emp.name} - في حالة احتياط (راحة)")
    
    # 📨 إرسال إشعارات تليغرام للموظفين العاملين
    print("\n📤 إرسال الإشعارات...")
    for emp, sonar in work_assignments:
        msg = (
            f"📢 تم تجهيز تبديلك القادم!\n"
            f"🕒 الفترة الرسمية: {official_window_label}\n"
            f"📡 السونار: {sonar.name}\n"
            f"✅ تم إعلامك مبكراً لتعرف وجهتك قبل نصف ساعة.\n\n"
            f"📊 إجمالي ساعات عملك: {emp.total_work_hours:.1f} ساعة"
        )
        send_telegram_message(emp.telegram_id, msg)
    
    # 📨 إرسال إشعارات للموظفين في الاحتياط
    for emp in standby_assignments:
        msg = (
            f"💤 أنت في حالة احتياط (راحة) للفترة الرسمية: {official_window_label}\n"
            f"🕒 الشفت: {shift.name}\n"
            f"📊 إجمالي ساعات عملك: {emp.total_work_hours:.1f} ساعة\n"
            f"🔄 مرات الراحة المتتالية: {emp.consecutive_rest_count}\n\n"
            f"✨ سيتم إعطاؤك الأولوية في التبديل القادم!"
        )
        send_telegram_message(emp.telegram_id, msg)
    
    # ✅ تأكيد اكتمال العملية بنجاح
    print(f"\n✅ تم توزيع {len(work_assignments)} موظف للعمل في الشفت {shift.name}")
    print(f"💤 تم تسجيل {len(standby_assignments)} موظف في حالة احتياط")
    print(f"⏰ الفترة الرسمية: {official_window_label}")
    
    # 🕐 تحديث وقت آخر تبديل في الإعدادات
    settings.update_last_rotation_time()
    print(f"🕐 تم تحديث آخر وقت تبديل: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M')}")
    
    # 📊 عرض ملخص التوزيع المفصل
    print("\n📊 ملخص التوزيع:")
    print("="*60)
    for sonar in active_sonars:
        count = sonar_assignment_count[sonar.id]
        print(f"  🏢 {sonar.name}: {count}/{sonar.max_employees} موظف")
    
    print(f"\n  💼 إجمالي العاملين: {len(work_assignments)}")
    print(f"  💤 إجمالي الاحتياط: {len(standby_assignments)}")
    print(f"  👥 إجمالي الموظفين: {len(employees)}")
    print("="*60)


def cancel_expired_confirmations():
    """إشعار المشرف بالتبديلات التي لم يؤكدها الموظف (بدون رفض تلقائي)"""
    from datetime import timedelta

    now = timezone.localtime(timezone.now())
    settings = SystemSettings.get_current_settings()
    rotation_hours = settings.get_effective_rotation_hours()

    # البحث عن التبديلات التي:
    # 1. مر عليها وقت كافٍ (rotation_hours)
    # 2. الموظف لم يؤكد (employee_confirmed = False)
    # 3. لم يتم تأكيدها نهائياً
    cutoff_time = now - timedelta(hours=rotation_hours)

    unconfirmed_assignments = EmployeeAssignment.objects.filter(
        assigned_at__lt=cutoff_time,  # مر عليها أكثر من فترة التبديل
        employee_confirmed=False,  # الموظف لم يؤكد
        confirmed=False  # لم يتم تأكيدها نهائياً
    ).select_related('employee', 'sonar', 'shift')

    notified_count = 0

    for assignment in unconfirmed_assignments:
        # حساب كم ساعة/دقيقة مرت منذ وقت التبديل
        time_passed = now - assignment.assigned_at
        hours_passed = time_passed.total_seconds() / 3600

        # التحقق من عدم إرسال نفس الإشعار مسبقاً (تجنب التكرار)
        # نستخدم EarlyNotification لتتبع الإشعارات المرسلة
        notification_exists = EarlyNotification.objects.filter(
            assignment=assignment,
            notification_type='admin',
            notification_stage='unconfirmed_warning'  # مرحلة جديدة للتحذير
        ).exists()

        if notification_exists:
            # تم إرسال الإشعار مسبقاً، تخطي
            continue

        print(
            f"⚠️ تبديل غير مؤكد: {assignment.employee.name} → {assignment.sonar.name} (مر عليه {hours_passed:.1f} ساعة)")

        # إرسال إشعار للمشرفين فقط (بدون رفض تلقائي)
        supervisors = User.objects.filter(
            models.Q(is_superuser=True) | models.Q(supervisor_profile__is_active=True)
        ).distinct()

        for supervisor in supervisors:
            if hasattr(supervisor, 'supervisor_profile') and supervisor.supervisor_profile.phone:
                supervisor_message = f"""
⚠️ تحذير: موظف لم يؤكد التبديل

👤 الموظف: {assignment.employee.name}
📡 السونار: {assignment.sonar.name}
🕐 الشفت: {assignment.shift.get_name_display()}
⏰ وقت التبديل: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M')}
⏳ مر عليه: {int(hours_passed)} ساعة
❓ الحالة: لم يؤكد الموظف

📋 يرجى المتابعة مع الموظف واتخاذ القرار المناسب:
- تأكيد التبديل يدوياً
- أو رفض التبديل يدوياً

⚠️ لن يتم الرفض تلقائياً - القرار بيدك.
                """
                send_telegram_message(supervisor.supervisor_profile.phone, supervisor_message)

        # حفظ سجل الإشعار لتجنب التكرار
        EarlyNotification.objects.create(
            assignment=assignment,
            notification_type='admin',
            notification_stage='unconfirmed_warning',
            minutes_before=0  # إشعار بعد انتهاء المدة
        )

        notified_count += 1

    if notified_count > 0:
        print(f"📢 تم إرسال {notified_count} إشعار للمشرفين عن تبديلات غير مؤكدة")
    else:
        print("✓ جميع التبديلات إما مؤكدة أو تم الإشعار عنها مسبقاً")

    return notified_count


def create_default_shifts():
    """إنشاء الشفتات الافتراضية الثلاثة إذا لم تكن موجودة"""
    from .models import Shift
    
    shifts_data = [
        {'name': 'morning', 'start_hour': 7, 'end_hour': 15},
        {'name': 'evening', 'start_hour': 15, 'end_hour': 23},
        {'name': 'night', 'start_hour': 23, 'end_hour': 7},
    ]
    
    created_count = 0
    for shift_data in shifts_data:
        shift, created = Shift.objects.get_or_create(
            name=shift_data['name'],
            defaults={
                'start_hour': shift_data['start_hour'],
                'end_hour': shift_data['end_hour']
            }
        )
        if created:
            print(f"✅ تم إنشاء شفت: {shift.get_name_display()}")
            created_count += 1
    
    if created_count == 0:
        print("✓ الشفتات موجودة مسبقاً")
    else:
        print(f"✅ تم إنشاء {created_count} شفت")
    
    return created_count
