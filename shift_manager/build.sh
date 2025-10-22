#!/usr/bin/env bash
set -o errexit

# تثبيت المكتبات المطلوبة
pip install -r requirements.txt

# تجميع الملفات الثابتة (CSS, JavaScript, Images)
echo "🔧 تجميع الملفات الثابتة..."
python manage.py collectstatic --no-input --clear

# تشغيل Migrations
echo "🔧 تنفيذ Migrations..."
python manage.py migrate --no-input

echo "✅ البناء اكتمل بنجاح!"

