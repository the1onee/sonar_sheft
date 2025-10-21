from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import Employee, Sonar, Shift, EmployeeAssignment, WeeklyShiftAssignment, SystemSettings, Manager, Supervisor, CustomNotification

# Form لإضافة موظف (مع أو بدون حساب)
class EmployeeForm(forms.ModelForm):
    # حقول اختيارية لإنشاء حساب
    create_account = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='إنشاء حساب لهذا الموظف؟'
    )
    username = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        }),
        label='اسم المستخدم'
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        }),
        label='كلمة المرور'
    )
    password_confirm = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور'
        }),
        label='تأكيد كلمة المرور'
    )
    
    class Meta:
        model = Employee
        fields = ['name', 'telegram_id', 'is_on_leave']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الموظف'
            }),
            'telegram_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'معرف التليجرام (اختياري)'
            }),
            'is_on_leave': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'اسم الموظف',
            'telegram_id': 'معرف التليجرام',
            'is_on_leave': 'في إجازة؟'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        create_account = cleaned_data.get('create_account')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        # إذا تم اختيار إنشاء حساب
        if create_account:
            if not username:
                raise forms.ValidationError('يجب إدخال اسم المستخدم عند إنشاء حساب')
            if not password:
                raise forms.ValidationError('يجب إدخال كلمة المرور عند إنشاء حساب')
            if password != password_confirm:
                raise forms.ValidationError('كلمات المرور غير متطابقة!')
            
            # التحقق من عدم تكرار اسم المستخدم
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError(f'اسم المستخدم "{username}" موجود مسبقاً!')
        
        return cleaned_data

# Form لإضافة سونار
class SonarForm(forms.ModelForm):
    class Meta:
        model = Sonar
        fields = ['name', 'active', 'max_employees']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم السونار'
            }),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_employees': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'عدد الموظفين'
            }),
        }
        labels = {
            'name': 'اسم السونار',
            'active': 'نشط؟',
            'max_employees': 'الحد الأقصى للموظفين'
        }

# Form لإضافة شفت
class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_hour', 'end_hour']
        widgets = {
            'name': forms.Select(attrs={'class': 'form-control'}),
            'start_hour': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 23,
                'placeholder': 'ساعة البداية (0-23)'
            }),
            'end_hour': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 23,
                'placeholder': 'ساعة النهاية (0-23)'
            }),
        }
        labels = {
            'name': 'نوع الشفت',
            'start_hour': 'ساعة البداية',
            'end_hour': 'ساعة النهاية'
        }

# Form لإسناد موظف إلى سونار وشفت
# shifts/forms.py


class EmployeeAssignmentForm(forms.ModelForm):
    class Meta:
        model = EmployeeAssignment
        fields = ['employee', 'sonar', 'shift', 'assigned_at']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'sonar': forms.Select(attrs={'class': 'form-control'}),
            'shift': forms.Select(attrs={'class': 'form-control'}),
            'assigned_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            })
        }
        labels = {
            'employee': 'الموظف',
            'sonar': 'السونار',
            'shift': 'الشفت',
            'assigned_at': 'تاريخ ووقت الإسناد'
        }

# Form لتسجيل الدخول (Login)
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        })
    )

# Form للجدولة الأسبوعية
class WeeklyShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = WeeklyShiftAssignment
        fields = ['shift', 'employees', 'week_start_date', 'week_end_date']
        widgets = {
            'shift': forms.Select(attrs={'class': 'form-control'}),
            'employees': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '10'
            }),
            'week_start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'week_end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }
        labels = {
            'shift': 'الشفت',
            'employees': 'الموظفين',
            'week_start_date': 'تاريخ بداية الأسبوع',
            'week_end_date': 'تاريخ نهاية الأسبوع'
        }
        help_texts = {
            'employees': 'اختر الموظفين الذين سيعملون في هذا الشفت خلال الأسبوع (استخدم Ctrl للاختيار المتعدد)',
        }

# ==================== Forms لإدارة الحسابات (Manager) ====================

class ManagerCreateForm(forms.ModelForm):
    """Form لإنشاء حساب مدير جديد"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        }),
        label='اسم المستخدم'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        }),
        label='كلمة المرور'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور'
        }),
        label='تأكيد كلمة المرور'
    )
    
    class Meta:
        model = Manager
        fields = ['name', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الكامل'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف'
            }),
        }
        labels = {
            'name': 'اسم المدير',
            'phone': 'رقم الهاتف'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('كلمات المرور غير متطابقة!')
        
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('اسم المستخدم موجود مسبقاً!')
        return username


class SupervisorCreateForm(forms.ModelForm):
    """Form لإنشاء حساب مشرف جديد"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        }),
        label='اسم المستخدم'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        }),
        label='كلمة المرور'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور'
        }),
        label='تأكيد كلمة المرور'
    )
    
    class Meta:
        model = Supervisor
        fields = ['name', 'phone', 'assigned_shift', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الكامل'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف'
            }),
            'assigned_shift': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'اسم المشرف',
            'phone': 'رقم الهاتف',
            'assigned_shift': 'الشفت المسؤول عنه',
            'is_active': 'نشط'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('كلمات المرور غير متطابقة!')
        
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('اسم المستخدم موجود مسبقاً!')
        return username


class EmployeeAccountCreateForm(forms.ModelForm):
    """Form لإنشاء حساب موظف جديد مع User"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اسم المستخدم'
        }),
        label='اسم المستخدم'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'كلمة المرور'
        }),
        label='كلمة المرور'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'تأكيد كلمة المرور'
        }),
        label='تأكيد كلمة المرور'
    )
    
    class Meta:
        model = Employee
        fields = ['name', 'telegram_id', 'is_on_leave']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الكامل'
            }),
            'telegram_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'معرف التليجرام (اختياري)'
            }),
            'is_on_leave': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'اسم الموظف',
            'telegram_id': 'معرف التليجرام',
            'is_on_leave': 'في إجازة'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('كلمات المرور غير متطابقة!')
        
        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('اسم المستخدم موجود مسبقاً!')
        return username


# ==================== Forms الأصلية ====================

# Form لإعدادات النظام
class SystemSettingsForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = ['rotation_interval_hours', 'early_notification_minutes', 'is_rotation_active']
        widgets = {
            'rotation_interval_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.5,
                'max': 24,
                'step': 0.5,
                'placeholder': 'مثال: 2.5 = كل ساعتين ونصف'
            }),
            'early_notification_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 120,
                'placeholder': 'مثال: 30 = قبل نصف ساعة'
            }),
            'is_rotation_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'rotation_interval_hours': 'فترة التبديل (بالساعات)',
            'early_notification_minutes': 'الإشعار المبكر (بالدقائق)',
            'is_rotation_active': 'تفعيل التبديل التلقائي'
        }
        help_texts = {
            'rotation_interval_hours': 'مثال: 2.5 = كل ساعتين ونصف، 3.0 = كل 3 ساعات (الفترة كما تدخلها بالضبط)',
            'early_notification_minutes': 'كم دقيقة قبل التبديل الفعلي يتم إرسال الإشعار للأدمن والموظفين',
            'is_rotation_active': 'تفعيل أو إيقاف نظام التبديل التلقائي'
        }


# Form للإشعارات المخصصة
class CustomNotificationForm(forms.ModelForm):
    class Meta:
        model = CustomNotification
        fields = ['title', 'message', 'send_to_all', 'target_employees']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان الإشعار'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'اكتب نص الإشعار هنا...'
            }),
            'send_to_all': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'target_employees': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'عنوان الإشعار',
            'message': 'نص الإشعار',
            'send_to_all': 'إرسال لجميع الموظفين',
            'target_employees': 'اختر موظفين محددين'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_employees'].required = False
