# 🚀 دليل النشر الكامل على Render

## 📋 الخدمات المطلوبة

عند رفع المشروع على Render، سيتم إنشاء **3 خدمات**:

| الخدمة | النوع | الوظيفة |
|-------|------|---------|
| 🌐 `shift-manager-web` | Web Service | تطبيق Django الرئيسي |
| ⚙️ `shift-manager-celery-worker` | Background Worker | تنفيذ المهام في الخلفية |
| ⏰ `shift-manager-celery-beat` | Background Worker | المهام المجدولة (التبديل التلقائي) |

---

## ✅ المتطلبات الأساسية

### 1️⃣ قاعدة بيانات PostgreSQL
يجب إنشاء قاعدة بيانات PostgreSQL على Render:
- اذهب إلى **Dashboard → New → PostgreSQL**
- اختر اسم مناسب مثل `shift-manager-db`
- احفظ بيانات الاتصال:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT` (عادةً 5432)

### 2️⃣ خدمة Redis (Upstash أو Render)
Redis مطلوب لـ Celery للتواصل بين الخدمات.

#### خيار A: Upstash Redis (مجاني ومستقر) ⭐
1. اذهب إلى [https://upstash.com/](https://upstash.com/)
2. سجل دخول/إنشاء حساب
3. أنشئ Redis Database
4. انسخ `REDIS_URL` (تبدأ بـ `rediss://`)

#### خيار B: Render Redis
1. Dashboard → New → Redis
2. اختر Free plan
3. انسخ `REDIS_URL`

### 3️⃣ بوت Telegram (اختياري)
إذا كنت تريد إرسال إشعارات Telegram:
1. تحدث مع [@BotFather](https://t.me/BotFather)
2. أنشئ بوت جديد بـ `/newbot`
3. احفظ `TELEGRAM_BOT_TOKEN`

---

## 🔧 خطوات النشر

### الخطوة 1: رفع الكود إلى GitHub
```bash
git add .
git commit -m "Ready for Render deployment with Celery Beat"
git push origin master
```

### الخطوة 2: إنشاء Blueprint على Render
1. اذهب إلى [https://dashboard.render.com/](https://dashboard.render.com/)
2. اضغط **New → Blueprint**
3. اختر الريبو الخاص بك `sonar_sheft`
4. Render سيكتشف ملف `render.yaml` تلقائياً
5. اضغط **Apply**

### الخطوة 3: إضافة متغيرات البيئة
سيطلب منك Render إضافة المتغيرات التالية لكل خدمة:

#### متغيرات مشتركة (لجميع الخدمات):
```
SECRET_KEY = (سيتم توليده تلقائياً للـ web service)
DEBUG = False
DB_NAME = shift_manager_db
DB_USER = your_db_user
DB_PASSWORD = your_db_password
DB_HOST = your_db_host.render.com
DB_PORT = 5432
REDIS_URL = rediss://your-redis-url
TELEGRAM_BOT_TOKEN = your_bot_token
```

**ملاحظة مهمة**: استخدم خاصية **sync** في Render لمشاركة المتغيرات بين الخدمات تلقائياً!

### الخطوة 4: انتظر اكتمال البناء
- ✅ Web Service: يستغرق 5-10 دقائق
- ✅ Celery Worker: يستغرق 3-5 دقائق  
- ✅ Celery Beat: يستغرق 3-5 دقائق

---

## 📊 التحقق من عمل النظام

### 1️⃣ التحقق من Web Service
افتح رابط التطبيق:
```
https://shift-manager-web.onrender.com
```

يجب أن ترى صفحة تسجيل الدخول ✅

### 2️⃣ التحقق من Celery Worker
في لوحة Render → `shift-manager-celery-worker` → **Logs**

يجب أن ترى:
```
[2024-01-XX] celery@worker ready.
```

### 3️⃣ التحقق من Celery Beat (الأهم!)
في لوحة Render → `shift-manager-celery-beat` → **Logs**

يجب أن ترى كل 10 دقائق:
```
[2024-01-XX] Scheduler: Sending due task rotate-shifts-dynamic
⏳ لم يحن وقت التبديل بعد | متبقي: 45.2 دقيقة | شفت: صباحي
```

أو عند التبديل:
```
⏰ نهاية الشيفت! صباحي | الوقت المتبقي: 8.5 دقيقة | تبديل مباشر
✅ تبديل نهاية الشيفت: صباحي → الشيفت التالي
```

---

## 🔍 استكشاف الأخطاء

### مشكلة: Celery Beat لا يعمل
**الأعراض**: لا توجد رسائل في Logs

**الحل**:
1. تأكد من `REDIS_URL` صحيح في Environment Variables
2. تأكد من تثبيت `celery` و `redis` في `requirements.txt`:
```
celery==5.3.4
redis==5.0.1
```
3. أعد تشغيل الخدمة: **Manual Deploy → Clear build cache & deploy**

### مشكلة: Redis Connection Error
**الأعراض**: `ConnectionError: Error connecting to Redis`

**الحل**:
1. تحقق من `REDIS_URL` في Environment Variables
2. تأكد من أن Redis يعمل (إذا كنت تستخدم Render Redis)
3. جرب Upstash Redis (أكثر استقراراً)

### مشكلة: التبديل لا يحدث
**الأعراض**: Celery Beat يعمل لكن لا تبديل

**الحل**:
1. تحقق من إعدادات النظام في Django Admin:
   - `/admin/shifts/systemsettings/`
   - تأكد من `is_rotation_active = True`
2. تحقق من وجود Shifts و Employees و Sonars
3. راجع Logs للأخطاء

### مشكلة: Database Migration Error
**الأعراض**: `django.db.migrations.exceptions.MigrationSListError`

**الحل**:
```bash
# في build.sh تأكد من وجود:
python manage.py migrate --noinput
```

---

## 📝 ملف render.yaml الكامل

```yaml
services:
  # خدمة Django Web Application
  - type: web
    name: shift-manager-web
    env: python
    region: oregon
    buildCommand: "chmod +x shift_manager/build.sh && ./shift_manager/build.sh"
    startCommand: "cd shift_manager && gunicorn shift_manager.wsgi:application --bind 0.0.0.0:$PORT"
    envVars:
      # ... (كما في الملف الحالي)

  # خدمة Celery Worker
  - type: worker
    name: shift-manager-celery-worker
    env: python
    region: oregon
    buildCommand: "pip install -r shift_manager/requirements.txt"
    startCommand: "cd shift_manager && celery -A shift_manager worker --loglevel=info"
    envVars:
      # ... (مشابه للـ web service)

  # خدمة Celery Beat
  - type: worker
    name: shift-manager-celery-beat
    env: python
    region: oregon
    buildCommand: "pip install -r shift_manager/requirements.txt"
    startCommand: "cd shift_manager && celery -A shift_manager beat --loglevel=info"
    envVars:
      # ... (مشابه للـ web service)
```

---

## 🎯 التحقق النهائي - قائمة المراجعة

قبل النشر، تأكد من:

- [ ] ✅ الكود محدّث على GitHub
- [ ] ✅ `render.yaml` يحتوي على 3 خدمات
- [ ] ✅ `requirements.txt` يحتوي على celery و redis
- [ ] ✅ قاعدة بيانات PostgreSQL جاهزة
- [ ] ✅ Redis جاهز (Upstash أو Render)
- [ ] ✅ متغيرات البيئة كاملة
- [ ] ✅ `ALLOWED_HOSTS` يحتوي على النطاق

بعد النشر:

- [ ] ✅ Web Service يعمل (صفحة تسجيل الدخول تظهر)
- [ ] ✅ Celery Worker يعمل (Logs تظهر "ready")
- [ ] ✅ Celery Beat يعمل (Logs تظهر المهام المجدولة)
- [ ] ✅ التبديل التلقائي يعمل (راجع Logs بعد 10 دقائق)

---

## 🎊 تهانينا!

إذا اكتملت جميع الخطوات، النظام الآن يعمل **بالكامل** على Render! 🚀

### الخدمات تعمل الآن:
1. ✅ تطبيق Django (الموقع الرئيسي)
2. ✅ Celery Worker (معالجة المهام)
3. ✅ Celery Beat (التبديل التلقائي كل 10 دقائق)

### التبديل التلقائي نشط:
- ⏱️ كل X ساعات داخل الشيفت (حسب الإعدادات)
- ⏰ مباشرة عند نهاية كل شيفت
- 🔍 فحص كل 10 دقائق

**استمتع بالنظام! 🎉**

