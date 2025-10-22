@echo off
echo ========================================
echo تشغيل Celery Worker و Beat
echo ========================================
echo.

echo انسخ .env.local الى .env اولا:
copy .env.local .env

echo.
echo الان شغل في 2 terminals:
echo.
echo Terminal 1:
echo   celery -A shift_manager worker --loglevel=info --pool=solo
echo.
echo Terminal 2:
echo   celery -A shift_manager beat --loglevel=info
echo.
pause

