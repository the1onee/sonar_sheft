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
BOT_TOKEN = os.getenv(
    'TELEGRAM_BOT_TOKEN',
    '7308309352:AAEXhAYReJDDETe3Mkb4B8eCfAdY-k-im2k'
)


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
    """فحص التبديلات القادمة وإرسال إشعارات مبكرة ومتكررة للأدمن والموظفين
    
    نظام الإشعارات:
    - إشعار أولي قبل 30 دقيقة
    - إشعارات تذكير كل 10 دقائق (عند 20 دقيقة، 10 دقائق)
    - إشعار نهائي عند وقت التبديل الفعلي
    """
    settings = SystemSettings.get_current_settings()
    
    if not settings.is_rotation_active:
        print("🔕 التبديل التلقائي معطل - لن يتم إرسال إشعارات")
        return
    
    now = timezone.localtime(timezone.now())
    
    # الأوقات المطلوبة للإشعارات: 30، 20، 10، 0 دقيقة
    notification_times = [
        {'minutes': 30, 'stage': 'initial', 'emoji': '⏰', 'message_prefix': 'إشعار أولي'},
        {'minutes': 20, 'stage': 'reminder', 'emoji': '⏱️', 'message_prefix': 'تذكير'},
        {'minutes': 10, 'stage': 'reminder', 'emoji': '⚠️', 'message_prefix': 'تذكير عاجل'},
        {'minutes': 0, 'stage': 'final', 'emoji': '🔔', 'message_prefix': 'وقت التبديل الآن'}
    ]
    
    notifications_sent = 0
    
    # إرسال إشعارات للأدمن (المشرفين)
    admins_and_supervisors = User.objects.filter(
        models.Q(is_superuser=True) | models.Q(supervisor_profile__is_active=True)
    ).distinct()
    
    # فحص كل وقت من أوقات الإشعارات
    for notification_time in notification_times:
        minutes_before = notification_time['minutes']
        stage = notification_time['stage']
        emoji = notification_time['emoji']
        message_prefix = notification_time['message_prefix']
        
        # نافذة زمنية ± 2 دقيقة لمرونة أكبر
        window_start = now + timedelta(minutes=minutes_before - 2)
        window_end = now + timedelta(minutes=minutes_before + 2)
        
        # البحث عن التبديلات في هذه النافذة
        upcoming_assignments = EmployeeAssignment.objects.filter(
            assigned_at__gte=window_start,
            assigned_at__lte=window_end,
            confirmed=False  # فقط التبديلات غير المؤكدة
        ).select_related('employee', 'sonar', 'shift')
        
        for assignment in upcoming_assignments:
            minutes_remaining = int((assignment.assigned_at - now).total_seconds() / 60)
            
            # التحقق من عدم إرسال نفس نوع الإشعار مسبقاً
            admin_notification_exists = EarlyNotification.objects.filter(
                assignment=assignment,
                notification_type='admin',
                notification_stage=stage,
                minutes_before=minutes_before
            ).exists()
            
            employee_notification_exists = EarlyNotification.objects.filter(
                assignment=assignment,
                notification_type='employee',
                notification_stage=stage,
                minutes_before=minutes_before
            ).exists()
            
            # إرسال للأدمن
            if not admin_notification_exists:
                if minutes_remaining >= 0:  # فقط إذا لم يمر الوقت بعد
                    admin_message = f"""
{emoji} {message_prefix} - تبديل قريب!

👤 الموظف: {assignment.employee.name}
📡 السونار: {assignment.sonar.name}
🕐 الشفت: {assignment.shift.get_name_display()}
⏰ وقت التبديل: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M')}
⏳ متبقي: {minutes_remaining} دقيقة

{"🎯 يجب أن يتوجه الموظف للسونار الآن!" if stage == 'final' else "يرجى تأكيد التبديل."}
                    """
                    
                    for admin in admins_and_supervisors:
                        if hasattr(admin, 'supervisor_profile'):
                            if admin.supervisor_profile.phone:
                                send_telegram_message(admin.supervisor_profile.phone, admin_message)
                        elif admin.is_superuser:
                            # يمكن إضافة رقم للأدمن في المستقبل
                            pass
                    
                    # حفظ سجل الإشعار
                    EarlyNotification.objects.create(
                        assignment=assignment,
                        notification_type='admin',
                        notification_stage=stage,
                        minutes_before=minutes_before
                    )
                    notifications_sent += 1
                    print(f"  ✅ إشعار أدمن ({message_prefix}): {assignment.employee.name} - متبقي {minutes_remaining} دقيقة")
            
            # إرسال للموظف
            if not employee_notification_exists and assignment.employee.telegram_id:
                if minutes_remaining >= 0:  # فقط إذا لم يمر الوقت بعد
                    # رسالة مخصصة حسب المرحلة
                    if stage == 'initial':
                        employee_message = f"""
{emoji} تنبيه مبكر - تبديل قريب!

مرحباً {assignment.employee.name}،

📡 السونار الجديد: {assignment.sonar.name}
🕐 الشفت: {assignment.shift.get_name_display()}
⏰ وقت التبديل: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M')}
⏳ متبقي: {minutes_remaining} دقيقة

يرجى الاستعداد للتوجه إلى موقعك الجديد.
                        """
                    elif stage == 'reminder':
                        employee_message = f"""
{emoji} تذكير - وقت التبديل يقترب!

{assignment.employee.name}،

📡 السونار: {assignment.sonar.name}
⏰ وقت التبديل: {assignment.assigned_at.strftime('%H:%M')}
⏳ متبقي: {minutes_remaining} دقيقة فقط!

⚡ ابدأ بالتحضير للانتقال الآن!
                        """
                    else:  # final
                        employee_message = f"""
{emoji} وقت التبديل الآن!

{assignment.employee.name}،

🎯 توجه فوراً إلى:
📡 السونار: {assignment.sonar.name}
🕐 الشفت: {assignment.shift.get_name_display()}

⏰ الوقت المحدد: الآن!
                        """
                    
                    send_telegram_message(assignment.employee.telegram_id, employee_message)
                    
                    # حفظ سجل الإشعار
                    EarlyNotification.objects.create(
                        assignment=assignment,
                        notification_type='employee',
                        notification_stage=stage,
                        minutes_before=minutes_before
                    )
                    notifications_sent += 1
                    print(f"  ✅ إشعار موظف ({message_prefix}): {assignment.employee.name} - متبقي {minutes_remaining} دقيقة")
    
    if notifications_sent > 0:
        print(f"📢 تم إرسال {notifications_sent} إشعار بنجاح")
    else:
        print("⏰ لا توجد تبديلات قادمة في نوافذ الإشعارات")


# 🔁 دالة تدوير الموظفين داخل الشفت (أي تبديل مواقعهم أو السونارات)
def rotate_within_shift(shift_name, rotation_hours=None):
    """تقوم هذه الدالة بتوزيع الموظفين على السونارات بشكل ذكي حسب سعة كل سونار"""
    print(f"🔁 بدء تدوير الشفت: {shift_name}")
    
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
    
    # استخدام الوقت المحلي (Asia/Baghdad) بدلاً من UTC
    now = timezone.localtime(timezone.now())

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

    # إنشاء قاموس لتعقب عدد المرات التي تم فيها تدوير كل موظف
    rotation_counter = {emp.id: 0 for emp in employees}

    # خلط ترتيب الموظفين عشوائيًا لتوزيع عادل
    random.shuffle(employees)
    
    # خلط السونارات أيضاً لتوزيع عشوائي
    random.shuffle(active_sonars)

    # 📊 قاموس لتتبع عدد الموظفين المعينين لكل سونار في هذا التدوير
    sonar_assignment_count = {sonar.id: 0 for sonar in active_sonars}
    
    # 📝 قائمة للموظفين الذين تم توزيعهم
    assigned_employees = []
    remaining_employees = employees.copy()

    # 🎯 المرحلة الأولى: توزيع موظف واحد على كل سونار نشط
    print("📍 المرحلة 1: توزيع موظف واحد لكل سونار...")
    for sonar in active_sonars:
        if not remaining_employees:
            break
            
        emp = remaining_employees.pop(0)
        
        # 🧾 حفظ التعيين الجديد في قاعدة البيانات
        EmployeeAssignment.objects.create(
            employee=emp,
            sonar=sonar,
            shift=shift,
            assigned_at=current_rotation_start,
            rotation_number=rotation_counter[emp.id] + 1
        )
        
        sonar_assignment_count[sonar.id] += 1
        rotation_counter[emp.id] += 1
        assigned_employees.append((emp, sonar))
        
        print(f"  ✅ {emp.name} → {sonar.name} (1/{sonar.max_employees})")

    # 🎯 المرحلة الثانية: توزيع الموظفين المتبقيين على السونارات التي تستوعب أكثر
    if remaining_employees:
        print(f"📍 المرحلة 2: توزيع {len(remaining_employees)} موظف متبقي...")
        
        for emp in remaining_employees:
            # البحث عن السونارات التي لم تصل لسعتها القصوى
            available_sonars = [
                sonar for sonar in active_sonars 
                if sonar_assignment_count[sonar.id] < sonar.max_employees
            ]
            
            if not available_sonars:
                print(f"  ⚠️ لا توجد سونارات متاحة للموظف {emp.name} - جميع السونارات ممتلئة")
                continue
            
            # اختيار سونار عشوائي من السونارات المتاحة
            new_sonar = random.choice(available_sonars)
            
            # 🧾 حفظ التعيين الجديد في قاعدة البيانات
            EmployeeAssignment.objects.create(
                employee=emp,
                sonar=new_sonar,
                shift=shift,
                assigned_at=current_rotation_start,
                rotation_number=rotation_counter[emp.id] + 1
            )
            
            sonar_assignment_count[new_sonar.id] += 1
            rotation_counter[emp.id] += 1
            assigned_employees.append((emp, new_sonar))
            
            print(f"  ✅ {emp.name} → {new_sonar.name} ({sonar_assignment_count[new_sonar.id]}/{new_sonar.max_employees})")

    # 📨 إرسال إشعارات تليغرام لجميع الموظفين
    print("📤 إرسال الإشعارات...")
    for emp, sonar in assigned_employees:
        msg = (
            f"📢 تم تعيينك في السونار الجديد: {sonar.name}\n"
            f"🕒 الشفت: {shift.name}\n"
            f"⏰ من {current_rotation_start.strftime('%H:%M')} إلى {current_rotation_end.strftime('%H:%M')}"
        )
        send_telegram_message(emp.telegram_id, msg)

    # ✅ تأكيد اكتمال العملية بنجاح
    print(f"✅ تم توزيع {len(assigned_employees)} موظف للشفت {shift.name} بنجاح")
    print(f"⏰ الفترة: {current_rotation_start.strftime('%H:%M')} - {current_rotation_end.strftime('%H:%M')}")
    
    # 🕐 تحديث وقت آخر تبديل في الإعدادات
    settings.update_last_rotation_time()
    print(f"🕐 تم تحديث آخر وقت تبديل: {timezone.localtime(timezone.now()).strftime('%Y-%m-%d %H:%M')}")
    
    # 📊 عرض ملخص التوزيع
    print("\n📊 ملخص التوزيع:")
    for sonar in active_sonars:
        count = sonar_assignment_count[sonar.id]
        print(f"  {sonar.name}: {count}/{sonar.max_employees} موظف")


def cancel_expired_confirmations():
    """وضع علامة على التبديلات المنتهية غير المؤكدة وإشعار المشرف"""
    from datetime import timedelta
    
    now = timezone.localtime(timezone.now())
    settings = SystemSettings.get_current_settings()
    rotation_hours = settings.get_effective_rotation_hours()
    
    # البحث عن التبديلات التي:
    # 1. مر عليها وقت كافٍ (rotation_hours)
    # 2. الموظف لم يؤكد (employee_confirmed = False)
    # 3. لم يتم تأكيدها نهائياً
    # 4. لم يتم وضع علامة عليها كمنتهية مسبقاً
    cutoff_time = now - timedelta(hours=rotation_hours)
    
    unconfirmed_assignments = EmployeeAssignment.objects.filter(
        assigned_at__lt=cutoff_time,  # مر عليها أكثر من فترة التبديل
        employee_confirmed=False,  # الموظف لم يؤكد
        confirmed=False,  # لم يتم تأكيدها نهائياً
        is_expired_unconfirmed=False  # لم يتم وضع علامة عليها مسبقاً
    ).select_related('employee', 'sonar', 'shift')
    
    marked_count = 0
    
    for assignment in unconfirmed_assignments:
        # حساب كم ساعة/دقيقة مرت منذ وقت التبديل
        time_passed = now - assignment.assigned_at
        hours_passed = time_passed.total_seconds() / 3600
        
        print(f"⚠️ تبديل غير مؤكد: {assignment.employee.name} → {assignment.sonar.name} (مر عليه {hours_passed:.1f} ساعة)")
        
        # وضع علامة على التبديل كمنتهي غير مؤكد
        assignment.is_expired_unconfirmed = True
        assignment.expired_at = now
        assignment.save()
        
        # إرسال إشعار للمشرفين
        supervisors = User.objects.filter(
            models.Q(is_superuser=True) | models.Q(supervisor_profile__is_active=True)
        ).distinct()
        
        for supervisor in supervisors:
            if hasattr(supervisor, 'supervisor_profile') and supervisor.supervisor_profile.phone:
                supervisor_message = f"""
⚠️ طلب منتهي غير مؤكد

👤 الموظف: {assignment.employee.name}
📡 السونار: {assignment.sonar.name}
🕐 الشفت: {assignment.shift.get_name_display()}
⏰ وقت التبديل: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M')}
⏳ مر عليه: {int(hours_passed)} ساعة
❓ الحالة: لم يؤكد الموظف وفات الوقت

📋 تم نقل الطلب إلى قائمة "الطلبات المنتهية"
يرجى مراجعة الطلبات المنتهية واتخاذ القرار:
- تأكيد التبديل يدوياً
- أو رفض التبديل يدوياً
                """
                send_telegram_message(supervisor.supervisor_profile.phone, supervisor_message)
        
        # حفظ سجل الإشعار لتجنب التكرار
        EarlyNotification.objects.create(
            assignment=assignment,
            notification_type='admin',
            notification_stage='unconfirmed_warning',
            minutes_before=0  # إشعار بعد انتهاء المدة
        )
        
        marked_count += 1
    
    if marked_count > 0:
        print(f"📢 تم وضع علامة على {marked_count} طلب كمنتهي غير مؤكد")
    else:
        print("✓ جميع التبديلات إما مؤكدة أو تم وضع علامة عليها مسبقاً")
    
    return marked_count