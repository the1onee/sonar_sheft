from datetime import date

from django.db import models
from django.db.models import ManyToManyField
from django.forms import DateField
from django.utils import timezone

class Employee(models.Model):
    name = models.CharField(max_length=100)
    telegram_id = models.CharField(max_length=50, null=True, blank=True)
    is_on_leave = models.BooleanField(default=False)  # لتحديد إذا الموظف في إجازة

    def __str__(self):
        return self.name


class Sonar(models.Model):
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)  # لتحديد إذا كانت المحطة نشطة
    max_employees = models.IntegerField(default=1)  # عدد الموظفين المطلوب لكل محطة

    def __str__(self):
        return self.name



class Shift(models.Model):
    SHIFT_CHOICES = [
        ('morning', 'صباحي'),
        ('evening', 'مسائي'),
        ('night', 'ليلي'),
    ]

    name = models.CharField(max_length=20, choices=SHIFT_CHOICES, unique=True)
    start_hour = models.IntegerField()
    end_hour = models.IntegerField()

    def __str__(self):
        return dict(self.SHIFT_CHOICES).get(self.name, self.name)

class WeeklyShiftAssignment(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    employees = ManyToManyField(Employee)  # ✅ جمع

    week_start_date = models.DateField(default=date.today)  # ✅ تاريخ افتراضي
    week_end_date = models.DateField(default=date.today)  # ✅ تاريخ افتراضي
    def __str__(self):
        return f"{self.shift.name} - {self.week_start_date}"


class EmployeeAssignment(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    sonar = models.ForeignKey(Sonar, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(default=timezone.now)
    rotation_number = models.IntegerField(default=0)
    confirmed = models.BooleanField(default=False)
    notification_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee} → {self.sonar} ({self.shift.name})"
