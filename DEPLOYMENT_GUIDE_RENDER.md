# دليل رفع المشروع على Render

## المتطلبات
- حساب على [Render](https://render.com)
- حساب GitHub (لربط المشروع)

## خطوات النشر

### الطريقة الأولى: استخدام render.yaml (موصى بها)

1. **رفع المشروع على GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Render deployment"
   git push origin master
   ```

2. **إنشاء خدمة جديدة على Render**
   - اذهب إلى [Render Dashboard](https://dashboard.render.com/)
   - اضغط على "New +" واختر "Blueprint"
   - اربط حساب GitHub الخاص بك
   - اختر المستودع الخاص بالمشروع
   - سيتم اكتشاف ملف `render.yaml` تلقائياً
   - اضغط "Apply"

3. **تكوين المتغيرات البيئية**
   
   سيتم إنشاء الخدمات التالية تلقائياً:
   - **Web Service**: خادم Django الرئيسي
   - **Celery Worker**: معالج المهام الخلفية
   - **Celery Beat**: جدولة المهام الدورية
   - **PostgreSQL Database**: قاعدة البيانات
   - **Redis**: لـ Celery message broker

4. **إضافة Domain مخصص (اختياري)**
   - في صفحة الخدمة، اذهب إلى "Settings"
   - في قسم "Custom Domain"، أضف النطاق الخاص بك
   - في إعدادات الخدمة، حدث `ALLOWED_HOSTS` لتشمل نطاقك

### الطريقة الثانية: النشر اليدوي

#### 1. إنشاء قاعدة بيانات PostgreSQL

1. في Render Dashboard، اضغط "New +" واختر "PostgreSQL"
2. املأ التفاصيل:
   - **Name**: shift-manager-db
   - **Database**: shift_manager_db
   - **User**: shift_manager_user
   - **Region**: اختر الأقرب لك
   - **Plan**: Starter (مجاني)
3. انتظر حتى يتم الإنشاء وانسخ رابط "Internal Database URL"

#### 2. إنشاء Redis

1. اضغط "New +" واختر "Redis"
2. املأ التفاصيل:
   - **Name**: shift-manager-redis
   - **Region**: نفس المنطقة التي اخترتها للـ database
   - **Plan**: Starter (مجاني)
3. انسخ رابط الاتصال "Redis URL"

#### 3. نشر Web Service (Django)

1. اضغط "New +" واختر "Web Service"
2. اربط GitHub repository
3. املأ التفاصيل:
   - **Name**: shift-manager-web
   - **Runtime**: Python 3
   - **Build Command**: `cd shift_manager && bash build.sh`
   - **Start Command**: `cd shift_manager && gunicorn shift_manager.wsgi:application`
   - **Plan**: Starter (مجاني)

4. أضف Environment Variables:
   ```
   SECRET_KEY=<generate-random-key>
   DEBUG=False
   DATABASE_URL=<paste-postgresql-url>
   REDIS_URL=<paste-redis-url>
   TIMEZONE=Asia/Baghdad
   ALLOWED_HOSTS=.onrender.com
   ```

#### 4. نشر Celery Worker

1. اضغط "New +" واختر "Background Worker"
2. اربط نفس GitHub repository
3. املأ التفاصيل:
   - **Name**: shift-manager-celery-worker
   - **Runtime**: Python 3
   - **Build Command**: `cd shift_manager && pip install -r requirements.txt`
   - **Start Command**: `cd shift_manager && celery -A shift_manager worker --loglevel=info`

4. أضف نفس Environment Variables من الخطوة السابقة

#### 5. نشر Celery Beat

1. اضغط "New +" واختر "Background Worker"
2. اربط نفس GitHub repository
3. املأ التفاصيل:
   - **Name**: shift-manager-celery-beat
   - **Runtime**: Python 3
   - **Build Command**: `cd shift_manager && pip install -r requirements.txt`
   - **Start Command**: `cd shift_manager && celery -A shift_manager beat --loglevel=info`

4. أضف نفس Environment Variables

## بعد النشر

### إنشاء مستخدم Admin

1. اذهب إلى Shell في Web Service:
   - في صفحة الخدمة، اضغط "Shell" من القائمة اليمنى
   
2. قم بتشغيل:
   ```bash
   cd shift_manager
   python manage.py createsuperuser
   ```

3. أدخل البيانات المطلوبة

### الوصول إلى لوحة التحكم

```
https://your-app-name.onrender.com/admin/
```

## كيفية عمل Celery في هذا المشروع

### المهام الدورية المجدولة

الـ Celery Beat يقوم بتشغيل المهام التالية تلقائياً:

1. **فحص الإشعارات المبكرة** (`check_early_notifications_task`)
   - يتم تشغيلها كل 2 دقيقة
   - تفحص الإشعارات التي يجب إرسالها قبل بداية الشفتات
   - يمكن للأدمن تحديد أوقات الإشعارات من لوحة التحكم

2. **تدوير الموظفين** (إذا تم تفعيله من الإعدادات)
   - يمكن للأدمن تحديد فترة التدوير من لوحة التحكم
   - يتم التدوير تلقائياً حسب الفترة المحددة

### تعديل جدول المهام

لتعديل جدول المهام، قم بتحديث ملف `shift_manager/shift_manager/celery.py`:

```python
app.conf.beat_schedule = {
    'check-early-notifications': {
        'task': 'shifts.tasks.check_early_notifications_task',
        'schedule': crontab(minute='*/2'),  # كل 2 دقيقة
    },
    # أضف مهام أخرى هنا
}
```

أمثلة على جدولة المهام:
```python
# كل ساعة
'schedule': crontab(minute=0, hour='*')

# كل يوم في الساعة 8 صباحاً
'schedule': crontab(minute=0, hour=8)

# كل يوم اثنين في الساعة 9 صباحاً
'schedule': crontab(minute=0, hour=9, day_of_week=1)

# كل 30 دقيقة
'schedule': crontab(minute='*/30')
```

## مراقبة الخدمات

### فحص Logs

في Render Dashboard:
1. اذهب إلى الخدمة (Web/Worker/Beat)
2. اضغط على "Logs" من القائمة اليمنى
3. ستظهر لك السجلات الحية

### التحقق من عمل Celery

في Celery Worker logs، يجب أن ترى:
```
[2025-10-21 10:00:00,000: INFO/MainProcess] Connected to redis://...
[2025-10-21 10:00:00,000: INFO/MainProcess] mingle: searching for neighbors
[2025-10-21 10:00:01,000: INFO/MainProcess] mingle: all alone
```

في Celery Beat logs، يجب أن ترى:
```
[2025-10-21 10:00:00,000: INFO/MainProcess] beat: Starting...
[2025-10-21 10:00:00,000: INFO/MainProcess] Scheduler: Sending due task check-early-notifications
```

## استكشاف الأخطاء

### خطأ في الاتصال بقاعدة البيانات
- تأكد من أن `DATABASE_URL` صحيح
- تأكد من أن الخدمة في نفس منطقة قاعدة البيانات

### خطأ في Celery
- تأكد من أن `REDIS_URL` صحيح
- تأكد من تشغيل Celery Worker و Beat

### مشكلة في الملفات الثابتة (Static Files)
- تأكد من تشغيل `python manage.py collectstatic` في build.sh
- تحقق من إعدادات Whitenoise في settings.py

## التحديثات المستقبلية

عند إجراء تحديثات على الكود:
```bash
git add .
git commit -m "Description of changes"
git push origin master
```

ستقوم Render بنشر التحديثات تلقائياً إذا كان Auto-Deploy مفعل.

## الأمان

⚠️ **مهم جداً:**
1. لا تشارك `SECRET_KEY` أبداً
2. تأكد من أن `DEBUG=False` في الإنتاج
3. قم بتحديث `ALLOWED_HOSTS` لتشمل نطاقك فقط
4. استخدم كلمات مرور قوية لقاعدة البيانات

## الدعم

للمزيد من المعلومات:
- [Render Docs](https://render.com/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Celery Documentation](https://docs.celeryq.dev/)

