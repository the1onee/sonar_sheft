from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps

def get_user_role(user):
    """
    تحديد دور المستخدم في النظام
    Returns: 'superadmin', 'manager', 'supervisor', 'employee', or None
    """
    if not user.is_authenticated:
        return None
    
    # سوبر أدمن
    if user.is_superuser:
        return 'superadmin'
    
    # مدير
    if hasattr(user, 'manager_profile') and user.manager_profile.is_active:
        return 'manager'
    
    # مشرف
    if hasattr(user, 'supervisor_profile') and user.supervisor_profile.is_active:
        return 'supervisor'
    
    # موظف
    if hasattr(user, 'employee_profile'):
        return 'employee'
    
    return None


def superadmin_required(view_func):
    """تتطلب صلاحيات سوبر أدمن فقط"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'يجب تسجيل الدخول أولاً')
            return redirect('login')
        
        if not request.user.is_superuser:
            messages.error(request, '⛔ هذه الصفحة مخصصة لسوبر أدمن فقط!')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """تتطلب صلاحيات مدير أو أعلى"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'يجب تسجيل الدخول أولاً')
            return redirect('login')
        
        role = get_user_role(request.user)
        if role not in ['superadmin', 'manager']:
            messages.error(request, '⛔ هذه الصفحة مخصصة للمديرين فقط!')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def supervisor_required(view_func):
    """تتطلب صلاحيات مشرف أو أعلى"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'يجب تسجيل الدخول أولاً')
            return redirect('login')
        
        role = get_user_role(request.user)
        if role not in ['superadmin', 'manager', 'supervisor']:
            messages.error(request, '⛔ هذه الصفحة مخصصة للمشرفين فقط!')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def employee_required(view_func):
    """تتطلب أن يكون المستخدم موظف (لديه حساب)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'يجب تسجيل الدخول أولاً')
            return redirect('login')
        
        role = get_user_role(request.user)
        if role not in ['superadmin', 'manager', 'supervisor', 'employee']:
            messages.error(request, '⛔ ليس لديك صلاحية الوصول!')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """تتطلب أن يكون المستخدم من الطاقم (مدير أو مشرف أو سوبر أدمن)"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'يجب تسجيل الدخول أولاً')
            return redirect('login')
        
        role = get_user_role(request.user)
        if role not in ['superadmin', 'manager', 'supervisor']:
            messages.error(request, '⛔ هذه الصفحة مخصصة للطاقم الإداري فقط!')
            return redirect('home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

