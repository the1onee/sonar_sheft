@echo off
title نظام إدارة السونار - تشغيل كامل
color 0A

echo.
echo ========================================
echo    نظام إدارة السونار
echo    تشغيل جميع الخدمات
echo ========================================
echo.

cd /d "%~dp0"

REM عرض معلومات IP
python get_ip.py
echo.

echo [1/3] بدء تشغيل Django Server...
start "Django Server" cmd /k "color 0B & title Django Server & python manage.py runserver 0.0.0.0:8000"
timeout /t 2 /nobreak >nul

echo [2/3] بدء تشغيل Celery Worker...
start "Celery Worker" cmd /k "color 0E & title Celery Worker & celery -A shift_manager worker --loglevel=info --pool=solo"
timeout /t 3 /nobreak >nul

echo [3/3] بدء تشغيل Celery Beat...
start "Celery Beat" cmd /k "color 0D & title Celery Beat & celery -A shift_manager beat --loglevel=info"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo تم تشغيل جميع الخدمات بنجاح!
echo ========================================
echo.
echo النوافذ المفتوحة:
echo  1. Django Server     - متاح على الشبكة المحلية
echo  2. Celery Worker     - معالج المهام
echo  3. Celery Beat       - المهام المجدولة
echo.
echo الوصول:
echo  - من نفس الجهاز:     http://localhost:8000
echo  - من أجهزة أخرى:     استخدم IP الموضح أعلاه
echo.
echo للاختبار، شغّل:
echo    check_celery.bat
echo.
echo لإيقاف كل شيء، أغلق جميع النوافذ
echo ========================================
echo.
pause

