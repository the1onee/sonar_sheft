@echo off
echo ========================================
echo تشغيل Celery لنظام إدارة السونار
echo ========================================
echo.

REM الانتقال إلى مجلد المشروع
cd /d "%~dp0"

echo [1/2] بدء تشغيل Celery Worker...
echo.
start "Celery Worker" cmd /k "celery -A shift_manager worker --loglevel=info --pool=solo"

timeout /t 3 /nobreak >nul

echo [2/2] بدء تشغيل Celery Beat (المهام المجدولة)...
echo.
start "Celery Beat" cmd /k "celery -A shift_manager beat --loglevel=info"

echo.
echo ========================================
echo تم تشغيل Celery بنجاح!
echo ========================================
echo.
echo سيتم تحديث الجدولة تلقائياً حسب الإعدادات
echo التي يضعها الأدمن في صفحة الإعدادات.
echo.
echo لإيقاف Celery، أغلق نوافذ الـ CMD المفتوحة.
echo ========================================
pause

