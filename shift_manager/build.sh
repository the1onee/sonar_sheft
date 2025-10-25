#!/usr/bin/env bash
set -o errexit

# تثبيت المكتبات المطلوبة
pip install -r requirements.txt

# التحقق من ملفات templates
echo "🔍 التحقق من ملفات templates..."
ls -la templates/reports/ || echo "⚠️ مجلد templates/reports غير موجود!"
if [ -f "templates/reports/employee_performance.html" ]; then
    echo "✅ ملف employee_performance.html موجود"
else
    echo "❌ ملف employee_performance.html غير موجود!"
fi

# تجميع الملفات الثابتة (CSS, JavaScript, Images)
echo "🔧 تجميع الملفات الثابتة..."
python manage.py collectstatic --no-input --clear

# تشغيل Migrations
echo "🔧 تنفيذ Migrations..."
python manage.py migrate --no-input

echo "✅ البناء اكتمل بنجاح!"

