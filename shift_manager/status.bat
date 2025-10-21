@echo off
echo.
echo ==========================================
echo    حالة الخدمات
echo ==========================================
echo.

echo فحص Django Server...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *runserver*" 2>nul | find /I /N "python.exe" > nul
if "%ERRORLEVEL%"=="0" (
    echo   Django Server:  ^| نشط
) else (
    echo   Django Server:  X متوقف
)

echo.
echo فحص Celery Worker...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *worker*" 2>nul | find /I /N "python.exe" > nul
if "%ERRORLEVEL%"=="0" (
    echo   Celery Worker:  ^| نشط
) else (
    echo   Celery Worker:  X متوقف
)

echo.
echo فحص Celery Beat...
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *beat*" 2>nul | find /I /N "python.exe" > nul
if "%ERRORLEVEL%"=="0" (
    echo   Celery Beat:    ^| نشط
) else (
    echo   Celery Beat:    X متوقف
)

echo.
echo ==========================================
echo.

echo العمليات الحالية:
tasklist | findstr /I "python.exe celery.exe"

echo.
echo ==========================================
echo.

pause

