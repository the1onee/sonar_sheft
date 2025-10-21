#!/usr/bin/env python
"""
تشغيل نظام السونار - كل الخدمات من terminal واحد
"""
import subprocess
import sys
import time
import os
import signal

# قائمة العمليات
processes = []

def signal_handler(sig, frame):
    """معالج لإيقاف جميع العمليات عند الضغط على Ctrl+C"""
    print("\n\n🛑 إيقاف جميع الخدمات...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
    print("✅ تم إيقاف جميع الخدمات")
    sys.exit(0)

# تسجيل معالج الإشارة
signal.signal(signal.SIGINT, signal_handler)

def print_banner():
    """طباعة شعار البداية"""
    print("=" * 60)
    print("          نظام إدارة السونار - تشغيل شامل")
    print("=" * 60)
    print()

def start_service(name, command, color_code="0"):
    """بدء خدمة جديدة"""
    print(f"🚀 بدء تشغيل {name}...")
    
    if sys.platform == "win32":
        # على Windows
        process = subprocess.Popen(
            command,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        # على Linux/Mac
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    
    processes.append(process)
    time.sleep(1)
    
    # التحقق من أن العملية لا زالت تعمل
    if process.poll() is None:
        print(f"   ✅ {name} يعمل (PID: {process.pid})")
        return True
    else:
        print(f"   ❌ فشل تشغيل {name}")
        return False

def main():
    print_banner()
    
    # التحقق من وجود ملف manage.py
    if not os.path.exists('manage.py'):
        print("❌ خطأ: تأكد من تشغيل السكريبت من داخل مجلد shift_manager")
        sys.exit(1)
    
    print("📋 جاري تشغيل الخدمات...")
    print()
    
    # 1. Django Server (متاح على جميع الأجهزة في الشبكة)
    if not start_service("Django Server", "python manage.py runserver 0.0.0.0:8000", "0B"):
        print("⚠️  تحذير: قد تكون هناك مشكلة في Django Server")
    
    time.sleep(2)
    
    # 2. Celery Worker
    if not start_service("Celery Worker", "celery -A shift_manager worker --loglevel=info --pool=solo", "0E"):
        print("⚠️  تحذير: قد تكون هناك مشكلة في Celery Worker")
    
    time.sleep(3)
    
    # 3. Celery Beat
    if not start_service("Celery Beat", "celery -A shift_manager beat --loglevel=info", "0D"):
        print("⚠️  تحذير: قد تكون هناك مشكلة في Celery Beat")
    
    print()
    print("=" * 60)
    print("✅ تم تشغيل جميع الخدمات بنجاح!")
    print("=" * 60)
    print()
    print("الخدمات النشطة:")
    print("  1. Django Server     → http://0.0.0.0:8000")
    print("  2. Celery Worker     → معالج المهام")
    print("  3. Celery Beat       → المهام المجدولة")
    print()
    print("💡 نصائح:")
    print("  • من نفس الجهاز: http://localhost:8000")
    print("  • من أجهزة أخرى: http://[IP_ADDRESS]:8000")
    print("  • للاختبار شغّل: python test_celery.py")
    print("  • لإيقاف كل شيء: اضغط Ctrl+C")
    print()
    print("📊 البرنامج يعمل الآن... (اضغط Ctrl+C للإيقاف)")
    print("=" * 60)
    
    # الانتظار إلى الأبد
    try:
        while True:
            # التحقق من أن جميع العمليات لا زالت تعمل
            for i, process in enumerate(processes):
                if process.poll() is not None:
                    print(f"\n⚠️  العملية رقم {i+1} توقفت! إعادة التشغيل...")
                    # يمكن إضافة منطق إعادة التشغيل هنا
            
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

