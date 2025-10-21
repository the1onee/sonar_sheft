@echo off
echo.
echo ==========================================
echo    إيقاف نظام السونار
echo ==========================================
echo.

REM إيقاف جميع عمليات Python (Django + Celery)
echo [1/4] إيقاف جميع عمليات Python...
taskkill /F /IM python.exe > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    ✓ تم إيقاف Python
) else (
    echo    ✓ لا توجد عمليات Python نشطة
)

REM إيقاف Celery
echo [2/4] إيقاف Celery...
taskkill /F /IM celery.exe > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo    ✓ تم إيقاف Celery
) else (
    echo    ✓ لا توجد عمليات Celery نشطة
)

REM إيقاف أي عملية تستخدم البورت 8000
echo [3/4] تحرير البورت 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a > nul 2>&1
)
echo    ✓ تم تحرير البورت 8000

echo [4/4] تنظيف...
timeout /t 1 /nobreak > nul

echo.
echo ==========================================
echo    تم إيقاف جميع الخدمات بنجاح ✓
echo ==========================================
echo.

pause

