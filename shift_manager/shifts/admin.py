from django.contrib import admin
from .models import Employee, Sonar, Shift, WeeklyShiftAssignment, EmployeeAssignment, Supervisor, AssignmentConfirmation, Manager

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'telegram_id', 'is_on_leave', 'created_at', 'created_by')
    list_filter = ('is_on_leave',)
    search_fields = ('name', 'telegram_id', 'user__username')

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
    list_display = ('employee', 'sonar', 'shift', 'assigned_at', 'employee_confirmed', 'employee_confirmed_at', 'supervisor_confirmed', 'supervisor_confirmed_at', 'confirmed')
    list_filter = ('shift', 'sonar', 'employee_confirmed', 'supervisor_confirmed', 'confirmed')
    search_fields = ('employee__name', 'sonar__name')
    readonly_fields = ('employee_confirmed_at', 'supervisor_confirmed_at')

@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'user__username', 'phone')

@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'assigned_shift', 'phone', 'is_active', 'created_at', 'created_by')
    list_filter = ('is_active', 'assigned_shift')
    search_fields = ('name', 'user__username', 'phone')

@admin.register(AssignmentConfirmation)
class AssignmentConfirmationAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'status', 'confirmed_by', 'confirmed_at')
    list_filter = ('status', 'confirmed_at')
    search_fields = (
        'assignment__employee__name', 
        'assignment__sonar__name',
        'confirmed_by__username'
    )
    readonly_fields = ('confirmed_at',)
