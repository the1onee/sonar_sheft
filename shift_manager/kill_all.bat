@echo off
REM إيقاف سريع لجميع خدمات السونار (بدون توقف)

taskkill /F /IM python.exe > nul 2>&1
taskkill /F /IM celery.exe > nul 2>&1

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a > nul 2>&1
)

echo ✓ تم إيقاف جميع الخدمات
timeout /t 2 /nobreak > nul

