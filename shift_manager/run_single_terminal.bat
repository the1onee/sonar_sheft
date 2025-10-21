@echo off
title نظام إدارة السونار
color 0A

echo.
echo ========================================
echo    نظام إدارة السونار
echo    تشغيل من terminal واحد
echo ========================================
echo.

cd /d "%~dp0"

REM عرض معلومات IP أولاً
python get_ip.py
echo.
echo جاري التشغيل...
echo.

REM تشغيل السكريبت
python run.py

pause

