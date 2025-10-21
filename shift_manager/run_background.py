#!/usr/bin/env python
"""
تشغيل الخدمات في الخلفية - terminal واحد
البديل الأبسط: يشغل كل شيء في نفس الـ terminal
"""
import subprocess
import sys
import os
import time
import threading

def run_django():
    """تشغيل Django Server"""
    print("🌐 Django Server يعمل على http://localhost:8000")
    subprocess.run([sys.executable, "manage.py", "runserver"])

def run_worker():
    """تشغيل Celery Worker"""
    print("⚙️  Celery Worker بدأ العمل...")
    subprocess.run(["celery", "-A", "shift_manager", "worker", 
                   "--loglevel=info", "--pool=solo"])

def run_beat():
    """تشغيل Celery Beat"""
    print("⏰ Celery Beat بدأ الجدولة...")
    subprocess.run(["celery", "-A", "shift_manager", "beat", 
                   "--loglevel=info"])

def main():
    print("=" * 60)
    print("          نظام إدارة السونار")
    print("=" * 60)
    print()
    
    # التحقق من المجلد
    if not os.path.exists('manage.py'):
        print("❌ خطأ: شغّل من داخل مجلد shift_manager")
        sys.exit(1)
    
    print("🚀 بدء تشغيل جميع الخدمات...")
    print()
    
    # إنشاء threads للخدمات
    threads = []
    
    # Django
    django_thread = threading.Thread(target=run_django, daemon=True)
    threads.append(django_thread)
    
    # Celery Worker
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    threads.append(worker_thread)
    
    # Celery Beat
    beat_thread = threading.Thread(target=run_beat, daemon=True)
    threads.append(beat_thread)
    
    # بدء جميع الـ threads
    for thread in threads:
        thread.start()
        time.sleep(1)
    
    print()
    print("=" * 60)
    print("✅ جميع الخدمات تعمل الآن!")
    print("=" * 60)
    print()
    print("افتح المتصفح: http://localhost:8000")
    print("اضغط Ctrl+C للإيقاف")
    print()
    
    # الانتظار
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 إيقاف الخدمات...")
        print("✅ تم الإيقاف")

if __name__ == "__main__":
    main()

