from django.urls import path
from . import views

urlpatterns = [
    # صفحة الهبوط (Landing Page)
    path('', views.landing_page, name='landing'),
    
    # الصفحة الرئيسية للمستخدمين المسجلين
    path('home/', views.home, name='home'),
    
    # المصادقة (Authentication)
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboards حسب الأدوار
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('dashboard/employee/', views.employee_dashboard, name='employee_dashboard'),
    
    # إدارة حسابات المديرين (سوبر أدمن فقط)
    path('accounts/managers/', views.manager_accounts_list, name='manager_accounts_list'),
    path('accounts/managers/create/', views.manager_account_create, name='manager_account_create'),
    path('accounts/managers/<int:pk>/toggle/', views.manager_account_toggle, name='manager_account_toggle'),
    path('accounts/managers/<int:pk>/delete/', views.manager_account_delete, name='manager_account_delete'),
    
    # إدارة حسابات المشرفين (مدير أو أعلى)
    path('accounts/supervisors/', views.supervisor_accounts_list, name='supervisor_accounts_list'),
    path('accounts/supervisors/create/', views.supervisor_account_create, name='supervisor_account_create'),
    path('accounts/supervisors/<int:pk>/toggle/', views.supervisor_account_toggle, name='supervisor_account_toggle'),
    path('accounts/supervisors/<int:pk>/delete/', views.supervisor_account_delete, name='supervisor_account_delete'),
    
    # إدارة حسابات الموظفين (مدير أو أعلى)
    path('accounts/employees/', views.employee_accounts_list, name='employee_accounts_list'),
    path('accounts/employees/create/', views.employee_account_create, name='employee_account_create'),
    path('accounts/employees/<int:pk>/delete/', views.employee_account_delete, name='employee_account_delete'),
    
    # إدارة الموظفين
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/update/', views.employee_update, name='employee_update'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    
    # إدارة السونارات
    path('sonars/', views.sonar_list, name='sonar_list'),
    path('sonars/create/', views.sonar_create, name='sonar_create'),
    path('sonars/<int:pk>/update/', views.sonar_update, name='sonar_update'),
    path('sonars/<int:pk>/delete/', views.sonar_delete, name='sonar_delete'),
    
    # إدارة الورديات
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/create/', views.shift_create, name='shift_create'),
    path('shifts/<int:pk>/update/', views.shift_update, name='shift_update'),
    path('shifts/<int:pk>/delete/', views.shift_delete, name='shift_delete'),
    
    # إدارة الجدولة الأسبوعية
    path('weekly-schedules/', views.weekly_schedule_list, name='weekly_schedule_list'),
    path('weekly-schedules/create/', views.weekly_schedule_create, name='weekly_schedule_create'),
    path('weekly-schedules/<int:pk>/update/', views.weekly_schedule_update, name='weekly_schedule_update'),
    path('weekly-schedules/<int:pk>/delete/', views.weekly_schedule_delete, name='weekly_schedule_delete'),
    
    # إدارة التبديلات المعلقة
    path('pending-assignments/', views.pending_assignments_list, name='pending_assignments_list'),
    path('pending-assignments/<int:pk>/confirm/', views.confirm_assignment, name='confirm_assignment'),
    path('pending-assignments/<int:pk>/reject/', views.reject_assignment, name='reject_assignment'),
    path('pending-assignments/bulk-confirm/', views.bulk_confirm_assignments, name='bulk_confirm_assignments'),
    path('confirmed-assignments/', views.confirmed_assignments_list, name='confirmed_assignments_list'),
    path('rejected-assignments/', views.rejected_assignments_list, name='rejected_assignments_list'),

    
    # التقارير
    path('reports/', views.reports_view, name='reports'),
    path('reports/employee-performance/', views.employee_performance_report, name='employee_performance_report'),
    path('reports/export/excel/', views.export_reports_excel, name='export_reports_excel'),
    path('reports/export/pdf/', views.export_reports_pdf, name='export_reports_pdf'),
    
    # إعدادات النظام
    path('settings/', views.settings_view, name='settings'),
    path('settings/update/', views.settings_update, name='settings_update'),
    
    # نظام التأكيد الثنائي
    path('assignments/<int:pk>/employee-confirm/', views.employee_confirm_assignment, name='employee_confirm_assignment'),
    path('assignments/<int:pk>/supervisor-confirm/', views.supervisor_confirm_assignment, name='supervisor_confirm_assignment'),
    
    # الإشعارات المخصصة
    path('notifications/send/', views.send_custom_notification, name='send_custom_notification'),
    path('notifications/', views.custom_notifications_list, name='custom_notifications_list'),
    path('notifications/<int:pk>/', views.custom_notification_detail, name='custom_notification_detail'),
]
