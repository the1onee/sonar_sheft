#!/bin/bash
# تشغيل سريع لنظام السونار على Linux/Mac من terminal واحد

echo "=========================================="
echo "   نظام إدارة السونار - تشغيل سريع"
echo "=========================================="
echo ""

# التحقق من المجلد
if [ ! -f "manage.py" ]; then
    echo "❌ خطأ: شغّل السكريبت من داخل مجلد shift_manager"
    exit 1
fi

# دالة لإيقاف جميع العمليات
cleanup() {
    echo ""
    echo "🛑 إيقاف جميع الخدمات..."
    kill $(jobs -p) 2>/dev/null
    echo "✅ تم الإيقاف"
    exit 0
}

# تسجيل معالج الإيقاف
trap cleanup SIGINT SIGTERM

echo "🚀 بدء تشغيل الخدمات..."
echo ""

# تشغيل Django في الخلفية
echo "🌐 تشغيل Django Server..."
python manage.py runserver > logs/django.log 2>&1 &
DJANGO_PID=$!
sleep 2

# تشغيل Celery Worker في الخلفية
echo "⚙️  تشغيل Celery Worker..."
celery -A shift_manager worker --loglevel=info --pool=solo > logs/worker.log 2>&1 &
WORKER_PID=$!
sleep 3

# تشغيل Celery Beat في الخلفية
echo "⏰ تشغيل Celery Beat..."
celery -A shift_manager beat --loglevel=info > logs/beat.log 2>&1 &
BEAT_PID=$!
sleep 2

echo ""
echo "=========================================="
echo "✅ جميع الخدمات تعمل!"
echo "=========================================="
echo ""
echo "الخدمات النشطة:"
echo "  • Django Server (PID: $DJANGO_PID)"
echo "  • Celery Worker (PID: $WORKER_PID)"
echo "  • Celery Beat   (PID: $BEAT_PID)"
echo ""
echo "افتح المتصفح: http://localhost:8000"
echo ""
echo "السجلات:"
echo "  • Django: tail -f logs/django.log"
echo "  • Worker: tail -f logs/worker.log"
echo "  • Beat:   tail -f logs/beat.log"
echo ""
echo "اضغط Ctrl+C للإيقاف"
echo "=========================================="
echo ""

# الانتظار
wait

