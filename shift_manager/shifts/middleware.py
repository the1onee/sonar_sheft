from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class RoleBasedAccessMiddleware:
    """
    Middleware لمنع المستخدمين غير السوبر أدمن من الدخول لصفحة /admin/
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # فحص إذا كان المستخدم يحاول الوصول لـ /admin/
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            # السماح فقط للسوبر أدمن
            if not request.user.is_superuser:
                # فحص دور المستخدم
                role = self.get_user_role(request.user)
                role_names = {
                    'manager': 'مدير',
                    'supervisor': 'مشرف',
                    'employee': 'موظف'
                }
                role_name = role_names.get(role, 'مستخدم')
                
                messages.error(
                    request, 
                    f'⛔ ليس لديك صلاحية الوصول لصفحة الإدارة (Admin). أنت {role_name} بصلاحيات محدودة.'
                )
                return redirect('home')
        
        response = self.get_response(request)
        return response
    
    def get_user_role(self, user):
        """تحديد دور المستخدم"""
        if not user.is_authenticated:
            return None
        
        if user.is_superuser:
            return 'superadmin'
        
        if hasattr(user, 'manager_profile') and user.manager_profile.is_active:
            return 'manager'
        
        if hasattr(user, 'supervisor_profile') and user.supervisor_profile.is_active:
            return 'supervisor'
        
        if hasattr(user, 'employee_profile'):
            return 'employee'
        
        return None

