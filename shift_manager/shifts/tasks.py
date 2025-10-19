# shifts/tasks.py
from celery import shared_task
from datetime import timedelta
import random
from django.utils import timezone
from .models import Shift, Sonar, Employee, WeeklyShiftAssignment, EmployeeAssignment
from .utils import rotate_within_shift


@shared_task
def rotate_shifts_task(rotation_hours=3):
    shifts = Shift.objects.all()
    for shift in shifts:
        try:
            rotate_within_shift(shift.name, rotation_hours)  # ✅ مرر shift.name وليس shift
        except Exception as e:
            print(f"❌ خطأ في شفت {shift.name}: {e}")


