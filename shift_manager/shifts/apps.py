from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class ShiftsConfig(AppConfig):
    name = 'shifts'

    def ready(self):
        from .models import Shift
        try:
            if not Shift.objects.exists():
                Shift.objects.create(name='morning', start_hour=7, end_hour=15)
                Shift.objects.create(name='evening', start_hour=15, end_hour=23)
                Shift.objects.create(name='night', start_hour=23, end_hour=7)
                print("✅ تم إنشاء الشفتات الثلاثة تلقائيًا.")
        except (OperationalError, ProgrammingError):
            # قاعدة البيانات قد لا تكون جاهزة أثناء أول ترحيل
            pass

