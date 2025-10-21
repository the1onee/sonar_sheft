@echo off
echo ========================================
echo فحص حالة Celery
echo ========================================
echo.

cd /d "%~dp0"

echo جاري فحص Celery...
echo.

python test_celery.py

echo.
echo ========================================
echo.
pause

