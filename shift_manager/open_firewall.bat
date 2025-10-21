@echo off
title فتح Firewall للمنفذ 8000
color 0C

echo.
echo ========================================
echo    فتح Firewall للوصول من الشبكة
echo ========================================
echo.
echo سيتم فتح المنفذ 8000 في Windows Firewall
echo للسماح للأجهزة الأخرى بالوصول للنظام
echo.
echo يجب تشغيل هذا الملف كمسؤول (Run as Administrator)
echo.
pause

echo.
echo جاري فتح المنفذ...
echo.

REM إضافة قاعدة Firewall للمنفذ 8000
netsh advfirewall firewall add rule name="Django Server - Port 8000" dir=in action=allow protocol=TCP localport=8000

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ تم فتح المنفذ 8000 بنجاح!
    echo ========================================
    echo.
    echo الآن يمكن للأجهزة الأخرى الوصول للنظام
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ فشل فتح المنفذ!
    echo ========================================
    echo.
    echo السبب المحتمل:
    echo   - لم يتم تشغيل الملف كمسؤول
    echo.
    echo الحل:
    echo   1. انقر بالزر الأيمن على هذا الملف
    echo   2. اختر "Run as administrator"
    echo   3. وافق على الطلب
    echo.
)

echo.
pause

