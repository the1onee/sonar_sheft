#!/usr/bin/env python
"""
اختبار نظام التبديل الجديد
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')
django.setup()

from shifts.models import SystemSettings
from django.utils import timezone

def test_rotation_system():
    print("=" * 60)
    print("🧪 اختبار نظام التبديل الجديد")
    print("=" * 60)
    print()
    
    # 1. الحصول على الإعدادات
    settings = SystemSettings.get_current_settings()
    print(f"✅ فترة التبديل: {settings.rotation_interval_hours} ساعة")
    print(f"✅ الإشعار المبكر: {settings.early_notification_minutes} دقيقة")
    print()
    
    # 2. عرض آخر تبديل
    if settings.last_rotation_time:
        last = timezone.localtime(settings.last_rotation_time)
        print(f"📅 آخر تبديل: {last.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"📅 آخر تبديل: لم يتم التبديل بعد")
    print()
    
    # 3. عرض التبديل التالي
    next_rotation = settings.get_next_rotation_time()
    next_local = timezone.localtime(next_rotation)
    print(f"⏰ التبديل التالي: {next_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 4. حساب الوقت المتبقي
    now = timezone.now()
    time_remaining = next_rotation - now
    hours = int(time_remaining.total_seconds() // 3600)
    minutes = int((time_remaining.total_seconds() % 3600) // 60)
    print(f"⏳ الوقت المتبقي: {hours} ساعة و {minutes} دقيقة")
    print()
    
    # 5. اختبار عدم تغير الوقت
    print("🔄 اختبار ثبات الوقت...")
    next1 = settings.get_next_rotation_time()
    next2 = settings.get_next_rotation_time()
    next3 = settings.get_next_rotation_time()
    
    if next1 == next2 == next3:
        print("✅ الوقت ثابت - لا يتغير! 🎉")
    else:
        print("❌ خطأ: الوقت يتغير!")
    print()
    
    print("=" * 60)
    print("✅ انتهى الاختبار")
    print("=" * 60)

if __name__ == '__main__':
    test_rotation_system()

