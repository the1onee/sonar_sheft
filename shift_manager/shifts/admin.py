from django.contrib import admin
from .models import Employee, Sonar, Shift, WeeklyShiftAssignment, EmployeeAssignment

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'is_on_leave')
    list_filter = ('is_on_leave',)
    search_fields = ('name', 'telegram_id')

@admin.register(Sonar)
class SonarAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'max_employees')
    list_filter = ('active',)
    search_fields = ('name',)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_hour', 'end_hour')

@admin.register(WeeklyShiftAssignment)
class WeeklyShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ['shift', 'week_start_date', 'week_end_date']  # ✅ الحقول الأصلية
    filter_horizontal = ('employees',)
    search_fields = ['shift__name']

@admin.register(EmployeeAssignment)
class EmployeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'sonar', 'shift', 'assigned_at', 'rotation_number', 'confirmed')
    list_filter = ('shift', 'sonar')
    search_fields = ('employee__name', 'sonar__name')
