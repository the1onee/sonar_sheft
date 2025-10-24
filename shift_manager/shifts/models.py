from datetime import date

from django.db import models
from django.db.models import ManyToManyField
from django.forms import DateField
from django.utils import timezone
from django.contrib.auth.models import User


class Manager(models.Model):
    """موديل المدير - مسؤول عن إضافة المشرفين والموظفين وإعدادات التبديل"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    name = models.CharField(max_length=100, verbose_name='اسم المدير')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='رقم الهاتف')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'مدير'
        verbose_name_plural = 'المديرين'

    def __str__(self):
        return self.name


class Supervisor(models.Model):
    """موديل المشرف - مسؤول عن الإجازات والتأكيدات وحالة السونارات"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supervisor_profile')
    name = models.CharField(max_length=100, verbose_name='اسم المشرف')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='رقم الهاتف')
    assigned_shift = models.ForeignKey('Shift', on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='supervisors', verbose_name='الشفت المسؤول عنه')
    is_active = models.BooleanField(default=True, verbose_name='نشط')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_supervisors', verbose_name='أنشئ بواسطة')

    class Meta:
        verbose_name = 'مشرف'
        verbose_name_plural = 'المشرفين'

    def __str__(self):
        return self.name

    def get_employees(self):
        """الحصول على الموظفين المخصصين لشفت المشرف"""
        if not self.assigned_shift:
            return Employee.objects.none()

        # الموظفين المسندين لهذا الشفت في الجدولة الأسبوعية
        from datetime import date
        today = date.today()

        # البحث في الجدولة الأسبوعية
        weekly_assignments = WeeklyShiftAssignment.objects.filter(
            shift=self.assigned_shift,
            week_start_date__lte=today,
            week_end_date__gte=today
        )

        employee_ids = set()
        for assignment in weekly_assignments:
            employee_ids.update(assignment.employees.values_list('id', flat=True))

        return Employee.objects.filter(id__in=employee_ids)


class Employee(models.Model):
    """موديل الموظف - مسؤول عن تأكيد التبديل فقط"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile', null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name='اسم الموظف')
    telegram_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='معرف تليجرام')
    is_on_leave = models.BooleanField(default=False, verbose_name='في إجازة')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='تاريخ الإنشاء')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='created_employees', verbose_name='أنشئ بواسطة')
    
    # 🔄 حقول نظام التبديل العادل
    total_work_hours = models.FloatField(default=0.0, verbose_name='إجمالي ساعات العمل')
    last_work_datetime = models.DateTimeField(null=True, blank=True, verbose_name='آخر وقت عمل')
    consecutive_rest_count = models.IntegerField(default=0, verbose_name='عدد مرات الراحة المتتالية')

    class Meta:
        verbose_name = 'موظف'
        verbose_name_plural = 'الموظفين'

    def __str__(self):
        return self.name
    
    def get_work_hours_today(self):
        """حساب ساعات العمل اليوم"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.localtime(timezone.now()).date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        
        assignments = EmployeeAssignment.objects.filter(
            employee=self,
            assigned_at__gte=today_start,
            is_standby=False  # فقط العمل الفعلي
        )
        
        # حساب إجمالي الساعات
        total_hours = 0.0
        for assignment in assignments:
            # افتراض أن كل تبديل يستمر حسب rotation_interval_hours
            settings = SystemSettings.get_current_settings()
            total_hours += settings.rotation_interval_hours
        
        return total_hours
    
    def get_priority_score(self, avg_work_hours=None):
        """حساب نقاط الأولوية (أقل = أولوية أعلى للعمل)
        
        يأخذ في الاعتبار:
        1. الفرق عن المتوسط (أهم عامل)
        2. الوقت منذ آخر عمل
        3. عدد مرات الراحة المتتالية
        """
        from django.utils import timezone
        
        # إذا لم يُعطى المتوسط، نحسبه
        if avg_work_hours is None:
            all_employees = Employee.objects.filter(is_on_leave=False)
            if all_employees.count() > 0:
                total = sum(emp.total_work_hours for emp in all_employees)
                avg_work_hours = total / all_employees.count()
            else:
                avg_work_hours = 0.0
        
        # ⭐ العامل الأهم: الفرق عن المتوسط
        # الموظف الذي عمل أقل من المتوسط → نقاط أقل (أولوية أعلى)
        # الموظف الذي عمل أكثر من المتوسط → نقاط أعلى (أولوية أقل)
        score = self.total_work_hours - avg_work_hours
        
        # ⭐ إذا لم يعمل الموظف أبداً → أولوية قصوى
        if self.total_work_hours == 0.0:
            score -= 1000
        
        # ⭐ مكافأة للموظفين الذين لم يعملوا مؤخراً
        if self.last_work_datetime:
            hours_since_work = (timezone.now() - self.last_work_datetime).total_seconds() / 3600
            # كل ساعة راحة = خصم 0.3 نقطة
            score -= (hours_since_work * 0.3)
        else:
            # لم يعمل أبداً → أولوية عالية جداً
            score -= 500
        
        # ⭐ مكافأة إضافية للموظفين الذين استراحوا عدة مرات متتالية
        # كل مرة راحة = خصم 5 نقاط
        score -= (self.consecutive_rest_count * 5)
        
        return score


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
    sonar = models.ForeignKey(Sonar, on_delete=models.CASCADE, null=True, blank=True)  # يمكن أن يكون null للاحتياط
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(default=timezone.now)
    rotation_number = models.IntegerField(default=0)
    confirmed = models.BooleanField(default=False)  # هل تم تأكيد التبديل؟
    notification_sent = models.BooleanField(default=False)  # هل تم إرسال الإشعار؟
    
    # 🔄 حقل جديد للتبديل العادل
    is_standby = models.BooleanField(default=False, verbose_name='في حالة احتياط')  # الموظف في راحة/احتياط
    work_duration_hours = models.FloatField(default=0.0, verbose_name='مدة العمل بالساعات')  # مدة العمل الفعلية

    # تأكيد الموظف
    employee_confirmed = models.BooleanField(default=False, verbose_name='تأكيد الموظف')
    employee_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت تأكيد الموظف')

    # تأكيد المشرف
    supervisor_confirmed = models.BooleanField(default=False, verbose_name='تأكيد المشرف')
    supervisor_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت تأكيد المشرف')
    supervisor_confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_assignments',
        verbose_name='المشرف المؤكد'
    )

    class Meta:
        verbose_name = 'إسناد موظف'
        verbose_name_plural = 'إسنادات الموظفين'
        ordering = ['-assigned_at']

    def __str__(self):
        if self.is_standby:
            return f"{self.employee} - احتياط ({self.shift.name})"
        return f"{self.employee} → {self.sonar} ({self.shift.name})"


class AssignmentConfirmation(models.Model):
    """موديل لتخزين تأكيدات/رفض التبديلات من قبل المشرف"""
    STATUS_CHOICES = [
        ('confirmed', 'مؤكد'),
        ('rejected', 'مرفوض'),
    ]

    assignment = models.OneToOneField(
        EmployeeAssignment,
        on_delete=models.CASCADE,
        related_name='confirmation',
        verbose_name='التبديل'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='الحالة'
    )
    confirmed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='تم التأكيد/الرفض بواسطة'
    )
    confirmed_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت التأكيد/الرفض')
    notes = models.TextField(blank=True, null=True, verbose_name='ملاحظات')

    class Meta:
        verbose_name = 'تأكيد تبديل'
        verbose_name_plural = 'تأكيدات التبديلات'
        ordering = ['-confirmed_at']

    def __str__(self):
        status_icon = '✅' if self.status == 'confirmed' else '❌'
        return f"{status_icon} {self.assignment} - {self.confirmed_at.strftime('%Y-%m-%d %H:%M')}"


class SystemSettings(models.Model):
    """موديل إعدادات النظام - إعدادات التبديل والإشعارات"""

    # إعدادات التبديل (ثابت: 3 ساعات)
    rotation_interval_hours = models.FloatField(
        default=3.0,
        verbose_name='فترة التبديل (بالساعات) - ثابتة',
        help_text='🔒 القيمة ثابتة: 3 ساعات (لا يمكن تغييرها من الواجهة)'
    )

    # إعدادات الإشعارات
    early_notification_minutes = models.IntegerField(
        default=30,
        verbose_name='الإشعار المبكر (بالدقائق)',
        help_text='كم دقيقة قبل التبديل الفعلي يتم إرسال الإشعار'
    )

    # إعدادات النظام
    is_rotation_active = models.BooleanField(
        default=True,
        verbose_name='تفعيل التبديل التلقائي'
    )

    # تتبع آخر تبديل
    last_rotation_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='آخر وقت تبديل',
        help_text='آخر وقت تم فيه تنفيذ التبديل التلقائي'
    )

    # تواريخ الإنشاء والتحديث
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ آخر تحديث')
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='آخر تحديث بواسطة'
    )

    class Meta:
        verbose_name = 'إعدادات النظام'
        verbose_name_plural = 'إعدادات النظام'

    def __str__(self):
        return f"إعدادات النظام - التبديل كل {self.rotation_interval_hours} ساعة"

    def get_effective_rotation_hours(self):
        """إرجاع ساعات التبديل كما هي (بدون طرح)"""
        return self.rotation_interval_hours

    def get_next_rotation_time(self):
        """حساب وقت التبديل التالي بناءً على آخر تبديل"""
        from datetime import timedelta

        # إذا كان هناك آخر تبديل، نحسب بناءً عليه
        if self.last_rotation_time:
            next_time = self.last_rotation_time + timedelta(hours=self.get_effective_rotation_hours())
        else:
            # إذا لم يتم التبديل بعد، نحسب من الوقت الحالي
            now = timezone.localtime(timezone.now())
            next_time = now + timedelta(hours=self.get_effective_rotation_hours())

        return next_time

    def update_last_rotation_time(self):
        """تحديث وقت آخر تبديل إلى الوقت الحالي"""
        self.last_rotation_time = timezone.now()
        self.save(update_fields=['last_rotation_time'])

    @classmethod
    def get_current_settings(cls):
        """الحصول على الإعدادات الحالية أو إنشاء إعدادات افتراضية"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'rotation_interval_hours': 3.0,
                'early_notification_minutes': 30,
                'is_rotation_active': True
            }
        )
        return settings


class EarlyNotification(models.Model):
    """موديل لتتبع الإشعارات المبكرة المرسلة"""
    assignment = models.ForeignKey(
        EmployeeAssignment,
        on_delete=models.CASCADE,
        related_name='early_notifications',
        verbose_name='التبديل'
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الإرسال')
    notification_type = models.CharField(
        max_length=20,
        choices=[('admin', 'إدمن'), ('employee', 'موظف')],
        verbose_name='نوع الإشعار'
    )
    notification_stage = models.CharField(
        max_length=30,
        choices=[
            ('initial', 'إشعار أولي (30 دقيقة)'),
            ('reminder', 'تذكير (كل 10 دقائق)'),
            ('final', 'إشعار نهائي (وقت التبديل)'),
            ('unconfirmed_warning', 'تحذير: لم يؤكد الموظف')
        ],
        default='initial',
        verbose_name='مرحلة الإشعار'
    )
    minutes_before = models.IntegerField(
        default=30,
        verbose_name='الدقائق المتبقية عند الإرسال'
    )

    class Meta:
        verbose_name = 'إشعار مبكر'
        verbose_name_plural = 'الإشعارات المبكرة'
        # إزالة unique_together للسماح بإشعارات متعددة

    def __str__(self):
        return f"إشعار {self.notification_type} - {self.get_notification_stage_display()} - {self.assignment}"


class CustomNotification(models.Model):
    """إشعارات مخصصة يرسلها المدير أو المشرف للموظفين"""
    title = models.CharField(max_length=200, verbose_name='عنوان الإشعار')
    message = models.TextField(verbose_name='نص الإشعار')
    sent_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='المرسل'
    )
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='وقت الإرسال')

    # الموظفون المستهدفون
    target_employees = models.ManyToManyField(
        Employee,
        blank=True,
        verbose_name='الموظفون المستهدفون',
        help_text='اترك فارغاً للإرسال لجميع الموظفين'
    )
    send_to_all = models.BooleanField(
        default=False,
        verbose_name='إرسال لجميع الموظفين'
    )

    # إحصائيات
    total_sent = models.IntegerField(default=0, verbose_name='عدد المرسل إليهم')

    class Meta:
        verbose_name = 'إشعار مخصص'
        verbose_name_plural = 'الإشعارات المخصصة'
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.title} - {self.sent_by.username} ({self.sent_at.strftime('%Y-%m-%d %H:%M')})"
