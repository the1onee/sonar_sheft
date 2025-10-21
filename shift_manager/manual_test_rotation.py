"""
اختبار يدوي لتنفيذ التبديل - لتجربة التبديل فوراً
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')
django.setup()

from shifts.tasks import rotate_shifts_task
from shifts.models import SystemSettings, EmployeeAssignment

print("=" * 60)
print("اختبار التبديل اليدوي - نظام إدارة السونار")
print("=" * 60)
print()

# عرض الإعدادات الحالية
settings = SystemSettings.get_current_settings()
print("⚙️  الإعدادات الحالية:")
print(f"   - فترة التبديل: {settings.rotation_interval_hours} ساعة")
print(f"   - حالة التبديل: {'🟢 نشط' if settings.is_rotation_active else '🔴 متوقف'}")
print()

# عرض آخر التبديلات
print("📊 آخر 5 تبديلات:")
last_assignments = EmployeeAssignment.objects.all().order_by('-assigned_at')[:5]
if last_assignments:
    for i, assignment in enumerate(last_assignments, 1):
        print(f"   {i}. {assignment.employee.name} → {assignment.sonar.name}")
        print(f"      الشفت: {assignment.shift.name} | التاريخ: {assignment.assigned_at.strftime('%Y-%m-%d %H:%M')}")
else:
    print("   لا توجد تبديلات سابقة")
print()

# تأكيد التنفيذ
print("⚠️  هل تريد تنفيذ التبديل الآن؟")
print("   سيتم تبديل الموظفين حسب الشفت الحالي")
print()
confirm = input("اكتب 'نعم' للتأكيد: ")

if confirm.strip().lower() in ['نعم', 'yes', 'y']:
    print()
    print("🔄 جاري تنفيذ التبديل...")
    print("-" * 60)
    
    try:
        # تنفيذ المهمة بشكل فوري (sync)
        rotate_shifts_task()
        
        print("-" * 60)
        print("✅ تم تنفيذ التبديل بنجاح!")
        print()
        
        # عرض التبديلات الجديدة
        print("📊 التبديلات الجديدة:")
        new_assignments = EmployeeAssignment.objects.all().order_by('-assigned_at')[:5]
        for i, assignment in enumerate(new_assignments, 1):
            status = "✅" if assignment.supervisor_confirmed else "⏳"
            print(f"   {status} {assignment.employee.name} → {assignment.sonar.name}")
            print(f"      الشفت: {assignment.shift.name} | الوقت: {assignment.assigned_at.strftime('%H:%M')}")
        
    except Exception as e:
        print("-" * 60)
        print(f"❌ حدث خطأ أثناء التبديل: {e}")
        import traceback
        traceback.print_exc()
else:
    print()
    print("❌ تم إلغاء التنفيذ")

print()
print("=" * 60)
print()

