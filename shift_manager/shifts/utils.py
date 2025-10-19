import requests
from datetime import timedelta
import random
from django.utils import timezone
from .models import Shift, Sonar, Employee, WeeklyShiftAssignment, EmployeeAssignment

BOT_TOKEN = "7308309352:AAEXhAYReJDDETe3Mkb4B8eCfAdY-k-im2k"

def send_telegram_message(chat_id, text):
    if not chat_id:
        print(f"❌ الموظف لا يملك chat_id")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, data=payload)
        print(f"تم الإرسال للـ chat_id {chat_id}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ خطأ في إرسال التليغرام: {e}")


def rotate_within_shift(shift_name, rotation_hours=3):
    """توزيع الموظفين على السونارات مع إرسال إشعارات"""
    now = timezone.now()

    try:
        shift = Shift.objects.get(name__iexact=shift_name.strip())
    except Shift.DoesNotExist:
        print(f"❌ الشفت {shift_name} غير موجود")
        return

    shift_start = now.replace(hour=shift.start_hour, minute=0, second=0, microsecond=0)
    shift_end = now.replace(hour=shift.end_hour, minute=0, second=0, microsecond=0)

    if shift.end_hour <= shift.start_hour:
        shift_end += timedelta(days=1)

    active_sonars = list(Sonar.objects.filter(active=True))
    if not active_sonars:
        print(f"❌ لا يوجد سونارات فعالة للشفت {shift_name}")
        return

    assignments = WeeklyShiftAssignment.objects.filter(
        shift=shift,
        week_start_date__lte=now.date(),
        week_end_date__gte=now.date()
    )

    employees = []
    for assignment in assignments:
        for emp in assignment.employees.all():
            if not emp.is_on_leave:
                # التحقق من وجود chat_id
                if not emp.telegram_id:
                    print(f"⚠️  الموظف {emp.name} لا يملك telegram_id")
                employees.append(emp)

    if not employees:
        print(f"❌ لا يوجد موظفين متاحين للشفت {shift_name}")
        return

    hours_since_start = (now - shift_start).total_seconds() / 3600
    rotation_index = int(hours_since_start // rotation_hours)
    current_rotation_start = shift_start + timedelta(hours=rotation_index * rotation_hours)
    current_rotation_end = current_rotation_start + timedelta(hours=rotation_hours)

    if current_rotation_end > shift_end:
        current_rotation_end = shift_end

    rotation_counter = {emp.id: 0 for emp in employees}
    available_employees = employees.copy()
    random.shuffle(available_employees)

    success_count = 0
    failed_count = 0

    for emp in available_employees:
        # اختيار سونار جديد عشوائي
        current_assignment = EmployeeAssignment.objects.filter(
            employee=emp, shift=shift
        ).order_by('-assigned_at').first()

        possible_sonars = [s for s in active_sonars
                           if not current_assignment or s != current_assignment.sonar]
        if not possible_sonars:
            possible_sonars = active_sonars

        new_sonar = random.choice(possible_sonars)

        # إنشاء التعيين
        EmployeeAssignment.objects.create(
            employee=emp,
            sonar=new_sonar,
            shift=shift,
            assigned_at=current_rotation_start,
            rotation_number=rotation_counter[emp.id] + 1
        )
        rotation_counter[emp.id] += 1

        # إرسال إشعار تليغرام فقط إذا كان هناك chat_id
        if emp.telegram_id:
            message = (
                f"📢 <b>تعيين جديد</b>\n"
                f"🎯 السونار: {new_sonar.name}\n"
                f"⏰ الشفت: {shift.name}\n"
                f"🕐 الوقت: {current_rotation_start.strftime('%H:%M')} - {current_rotation_end.strftime('%H:%M')}"
            )
            if send_telegram_message(emp.telegram_id, message):
                success_count += 1
            else:
                failed_count += 1
        else:
            failed_count += 1
            print(f"⚠️  لم يتم إرسال إشعار للموظف {emp.name} - لا يملك telegram_id")

    print(f"✅ تم التوزيع: {success_count} إشعار أُرسل، {failed_count} فشل")
    print(f"📅 الفترة: {current_rotation_start} إلى {current_rotation_end}")
