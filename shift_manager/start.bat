@echo off
cls
echo.
echo ==========================================
echo      نظام إدارة السونار
echo ==========================================
echo.
echo جاري التشغيل...
echo.

REM الانتقال للمجلد الصحيح
cd /d "%~dp0"

REM تشغيل Django على جميع الأجهزة في الشبكة
start /B python manage.py runserver 0.0.0.0:8000 > nul 2>&1

REM الانتظار قليلاً
timeout /t 2 /nobreak > nul

REM تشغيل Celery Worker في الخلفية
start /B celery -A shift_manager worker --loglevel=info --pool=solo > nul 2>&1

REM الانتظار قليلاً
timeout /t 3 /nobreak > nul

REM تشغيل Celery Beat في الخلفية
start /B celery -A shift_manager beat --loglevel=info > nul 2>&1

REM الانتظار قليلاً
timeout /t 2 /nobreak > nul

REM عرض معلومات IP
python get_ip.py

echo.
echo ==========================================
echo      تم التشغيل بنجاح!
echo ==========================================
echo.
echo الخدمات النشطة:
echo   - Django Server:  متاح على الشبكة المحلية
echo   - Celery Worker:  يعمل في الخلفية
echo   - Celery Beat:    يعمل في الخلفية
echo.
echo الوصول:
echo   - من نفس الجهاز:     http://localhost:8000
echo   - من أجهزة أخرى:     شاهد IP في الأعلى
echo.
echo للاختبار:
echo   python test_celery.py
echo.
echo لإيقاف الخدمات:
echo   stop.bat
echo.
echo ==========================================
echo.

REM فتح المتصفح تلقائياً
start http://localhost:8000

pause

