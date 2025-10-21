@echo off
echo ===================================
echo تثبيت المكتبات المطلوبة للتصدير
echo ===================================
echo.

pip install openpyxl>=3.1.0
pip install reportlab>=4.0.0
pip install arabic-reshaper>=3.0.0
pip install python-bidi>=0.4.2

echo.
echo ===================================
echo تم تثبيت جميع المكتبات بنجاح!
echo ===================================
echo.
echo الآن يمكنك تشغيل الخادم:
echo python manage.py runserver
echo.
pause

