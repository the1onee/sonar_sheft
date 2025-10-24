from django.contrib import admin
from .models import Employee, Sonar, Shift, WeeklyShiftAssignment, EmployeeAssignment, Supervisor, AssignmentConfirmation, Manager, SystemSettings, MonthlyWorkHoursReset

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

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('rotation_interval_hours', 'early_notification_minutes', 'is_rotation_active', 'last_rotation_time', 'updated_at', 'updated_by')
    list_filter = ('is_rotation_active',)
    # جعل rotation_interval_hours للقراءة فقط - ثابت عند 3 ساعات
    readonly_fields = ('rotation_interval_hours', 'last_rotation_time', 'created_at', 'updated_at')
    fieldsets = (
        ('⚙️ إعدادات التبديل', {
            'fields': ('rotation_interval_hours', 'is_rotation_active', 'last_rotation_time')
        }),
        ('📢 إعدادات الإشعارات', {
            'fields': ('early_notification_minutes',)
        }),
        ('📝 معلومات التحديث', {
            'fields': ('created_at', 'updated_at', 'updated_by')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """التأكد من أن rotation_interval_hours تبقى 3.0"""
        obj.rotation_interval_hours = 3.0  # 🔒 ثابت
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MonthlyWorkHoursReset)
class MonthlyWorkHoursResetAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'get_month_display', 'total_employees', 'total_hours_before_reset', 'average_hours_before_reset', 'reset_datetime')
    list_filter = ('year', 'month')
    search_fields = ('year', 'month')
    readonly_fields = ('year', 'month', 'total_employees', 'total_hours_before_reset', 'average_hours_before_reset', 'reset_datetime')
    
    def get_month_display(self, obj):
        """عرض اسم الشهر بالعربية"""
        return obj.get_month_name()
    get_month_display.short_description = 'اسم الشهر'
    
    def has_add_permission(self, request):
        """منع الإضافة اليدوية - يتم التسجيل تلقائياً"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """منع الحذف للحفاظ على السجلات"""
        return False
