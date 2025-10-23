from django.apps import AppConfig

class ShiftsConfig(AppConfig):
    name = 'shifts'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # تم تعطيل التحقق من الشفتات عند بدء التطبيق لتحسين الأداء
        # استخدم أمر: python manage.py shell
        # ثم: from shifts.utils import create_default_shifts; create_default_shifts()
        pass

