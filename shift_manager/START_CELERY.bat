@echo off
echo ========================================
echo 🚀 تشغيل Celery Worker و Beat
echo ========================================
echo.

REM التحقق من وجود ملف celery_config.env
if exist celery_config.env (
    echo ✅ تم العثور على celery_config.env
) else (
    echo ❌ لم يتم العثور على celery_config.env
    echo يرجى إنشاء الملف أولاً
    pause
    exit /b 1
)

echo.
echo 🔄 بدء تشغيل Celery Worker...
start "Celery Worker" cmd /k "celery -A shift_manager worker --loglevel=info --pool=solo"

timeout /t 2 /nobreak >nul

echo 🔄 بدء تشغيل Celery Beat...
start "Celery Beat" cmd /k "celery -A shift_manager beat --loglevel=info"

echo.
echo ✅ تم تشغيل Celery بنجاح!
echo.
echo 📋 المهام المجدولة:
echo   - rotate-shifts-dynamic: كل دقيقة (التحقق من الإعدادات)
echo   - check-early-notifications: كل دقيقتين (الإشعارات المبكرة)
echo.
echo ℹ️ ملاحظة: التبديل يعمل حسب الإعدادات التي تحددها في صفحة الإعدادات
echo.
pause

