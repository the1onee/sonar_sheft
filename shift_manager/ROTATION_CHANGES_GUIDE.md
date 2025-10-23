# 📋 دليل التغييرات الجديدة - نظام التبديل التلقائي

## ✅ التغييرات الرئيسية

### 1️⃣ **وقت التبديل التالي ثابت الآن!**

**قبل التعديل:**
- كان وقت "التبديل التالي" يُحسب من الوقت الحالي دائماً
- عند عمل Refresh → يتغير الوقت! 😓

**بعد التعديل:**
- يتم حفظ **آخر وقت تبديل** في قاعدة البيانات
- وقت التبديل التالي = **آخر تبديل + 3 ساعات** (ثابت)
- عند عمل Refresh → الوقت **لا يتغير** ✅

---

### 2️⃣ **الرفض التلقائي للتبديلات غير المؤكدة**

**قبل التعديل:**
- كانت هناك مهمة دورية تعمل كل 10 دقائق
- تظهر رسائل كثيرة في الـ logs

**بعد التعديل:**
- الرفض يحدث **عند بداية كل تبديل جديد فقط**
- إذا لم يؤكد الموظف التبديل السابق → يُرفض تلقائياً
- أقل رسائل في الـ logs ✅

---

## 🔧 التغييرات التقنية

### 📁 **الملفات المعدلة:**

#### 1. `shifts/models.py`
```python
# إضافة حقل جديد
last_rotation_time = models.DateTimeField(
    null=True,
    blank=True,
    verbose_name='آخر وقت تبديل'
)

# تعديل حساب التبديل التالي
def get_next_rotation_time(self):
    if self.last_rotation_time:
        # الحساب من آخر تبديل ✅
        next_time = self.last_rotation_time + timedelta(hours=...)
    else:
        # أول مرة: من الوقت الحالي
        next_time = now + timedelta(hours=...)
    return next_time

# دالة جديدة لتحديث آخر تبديل
def update_last_rotation_time(self):
    self.last_rotation_time = timezone.now()
    self.save()
```

#### 2. `shifts/utils.py`
```python
def rotate_within_shift(shift_name, rotation_hours=None):
    # ... إعدادات ...
    
    # ❌ رفض التبديلات السابقة غير المؤكدة أولاً
    rejected_count = cancel_expired_confirmations()
    
    # ... توزيع الموظفين الجديد ...
    
    # 🕐 تحديث آخر وقت تبديل
    settings.update_last_rotation_time()
```

#### 3. `shift_manager/celery.py`
```python
# تم حذف هذه المهمة:
# 'cancel-expired-confirmations': {
#     'task': 'shifts.tasks.cancel_expired_confirmations_task',
#     'schedule': crontab(minute='*/10'),
# },

# المهام المتبقية:
app.conf.beat_schedule = {
    'rotate-shifts-default': {
        'task': 'shifts.tasks.rotate_shifts_task',
        'schedule': timedelta(hours=3),
    },
    'check-early-notifications': {
        'task': 'shifts.tasks.check_early_notifications_task',
        'schedule': crontab(minute='*/2'),
    },
}
```

#### 4. `shifts/tasks.py`
```python
# تم حذف:
# @shared_task
# def cancel_expired_confirmations_task():
#     ...

# المهام المتبقية:
# - rotate_shifts_task ✅
# - check_early_notifications_task ✅
```

---

## 📊 Migration الجديد

تم إنشاء migration جديد:
```bash
shifts\migrations\0018_systemsettings_last_rotation_time.py
```

**لتطبيقه:**
```bash
cd shift_manager
python manage.py migrate
```

---

## 🚀 كيفية التشغيل

### للتشغيل المحلي:
```bash
cd shift_manager

# تشغيل Celery (طريقة سريعة):
START_CELERY.bat

# أو يدوياً:
# Terminal 1:
celery -A shift_manager worker --loglevel=info --pool=solo

# Terminal 2:
celery -A shift_manager beat --loglevel=info
```

### للتشغيل على Render:
- الـ Web Service يعمل على Render
- Celery يعمل على جهازك المحلي
- البيانات في PostgreSQL على Render (يصل إليها Celery)

---

## 📋 سير العمل الجديد

### عند تشغيل النظام:

1. **كل 3 ساعات** (أو حسب الإعدادات):
   ```
   🔄 تبدأ مهمة rotate_shifts_task
   ↓
   🔍 فحص التبديلات السابقة غير المؤكدة
   ↓
   ❌ رفض التبديلات غير المؤكدة (إن وجدت)
   ↓
   📨 إرسال إشعارات للموظفين والمشرفين
   ↓
   ✅ بدء التبديل الجديد (توزيع الموظفين)
   ↓
   🕐 حفظ وقت التبديل في last_rotation_time
   ↓
   📊 عرض ملخص التوزيع
   ```

2. **كل دقيقتين**:
   ```
   ⏰ فحص الإشعارات المبكرة
   - قبل 30 دقيقة من التبديل
   - قبل 20 دقيقة (تذكير)
   - قبل 10 دقائق (تذكير عاجل)
   - عند وقت التبديل (تذكير نهائي)
   ```

---

## 🧪 اختبار التغييرات

### 1. اختبار حفظ آخر وقت تبديل:
```bash
python manage.py shell
```

```python
from shifts.models import SystemSettings
from django.utils import timezone

# الحصول على الإعدادات
settings = SystemSettings.get_current_settings()

# عرض آخر تبديل
print("آخر تبديل:", settings.last_rotation_time)

# عرض التبديل التالي
print("التبديل التالي:", settings.get_next_rotation_time())

# تحديث يدوياً (للاختبار)
settings.update_last_rotation_time()
print("تم التحديث!")
print("آخر تبديل الآن:", settings.last_rotation_time)
```

### 2. اختبار التبديل التلقائي:
```bash
python manage.py shell
```

```python
from shifts.tasks import rotate_shifts_task

# تشغيل التبديل يدوياً
rotate_shifts_task()

# ستظهر:
# 🔁 بدء تدوير الشفت...
# 🔍 فحص التبديلات السابقة غير المؤكدة...
# ✓ لا توجد تبديلات منتهية للرفض (أو)
# ❌ تم رفض X تبديل غير مؤكد من الفترة السابقة
# ...
```

### 3. اختبار الرفض التلقائي:
```python
from shifts.utils import cancel_expired_confirmations
from shifts.models import SystemSettings
from datetime import timedelta
from django.utils import timezone

# الحصول على الإعدادات
settings = SystemSettings.get_current_settings()

# عرض فترة التبديل
print(f"فترة التبديل: {settings.rotation_interval_hours} ساعة")

# تشغيل الرفض التلقائي يدوياً
rejected = cancel_expired_confirmations()
print(f"تم رفض {rejected} تبديل")
```

---

## 📝 ملاحظات مهمة

### ✅ المزايا:
1. **وقت التبديل التالي ثابت** - لا يتغير مع كل Refresh
2. **أقل ضغط على النظام** - الرفض يحدث عند التبديل فقط
3. **logs أوضح** - رسائل أقل وأكثر فائدة
4. **تتبع أفضل** - نعرف متى تم آخر تبديل بالضبط

### ⚠️ تنبيهات:
1. **أول تشغيل**: `last_rotation_time` سيكون `None` (طبيعي)
2. **بعد التبديل الأول**: سيتم حفظ الوقت تلقائياً
3. **الرفض التلقائي**: يعتمد على `rotation_interval_hours` من الإعدادات

---

## 🔄 للرجوع للنظام القديم

إذا أردت الرجوع للنظام القديم (المهمة الدورية كل 10 دقائق):

1. أعد المهمة في `celery.py`:
```python
'cancel-expired-confirmations': {
    'task': 'shifts.tasks.cancel_expired_confirmations_task',
    'schedule': crontab(minute='*/10'),
},
```

2. أعد المهمة في `tasks.py`:
```python
@shared_task
def cancel_expired_confirmations_task():
    try:
        cancel_expired_confirmations()
    except Exception as e:
        print(f"❌ خطأ: {e}")
```

3. احذف استدعاء `cancel_expired_confirmations()` من `rotate_within_shift()`

---

## 🆘 المساعدة

### مشكلة: التبديل التالي لا يزال يتغير؟
**الحل:**
```bash
python manage.py migrate  # تأكد من تطبيق Migration
```

### مشكلة: الرفض التلقائي لا يعمل؟
**الحل:**
- تأكد من تشغيل Celery Worker و Beat
- تحقق من الـ logs

### مشكلة: أخطاء في الاستيراد؟
**الحل:**
```bash
pip install -r requirements.txt
```

---

## 📞 للدعم

إذا واجهت أي مشاكل، تحقق من:
1. Logs الخاصة بـ Celery Worker
2. Logs الخاصة بـ Celery Beat
3. قاعدة البيانات (`last_rotation_time`)

---

**آخر تحديث:** 2025-10-22
**النسخة:** 2.0 - نظام التبديل المُحسّن ✨

