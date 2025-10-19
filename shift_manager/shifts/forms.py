from django import forms
from .models import Employee, Sonar, Shift, EmployeeAssignment

# Form لإضافة موظف
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'telegram_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_id': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Form لإضافة سونار
class SonarForm(forms.ModelForm):
    class Meta:
        model = Sonar
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

# Form لإضافة شفت
class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_hour', 'end_hour']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_hour': forms.NumberInput(attrs={'class': 'form-control', 'min':0, 'max':23}),
            'end_hour': forms.NumberInput(attrs={'class': 'form-control', 'min':0, 'max':23}),
        }

# Form لإسناد موظف إلى سونار وشفت
# shifts/forms.py


class EmployeeAssignmentForm(forms.ModelForm):
    class Meta:
        model = EmployeeAssignment
        fields = ['employee', 'sonar', 'shift', 'assigned_at']
        widgets = {
            'assigned_at': forms.DateTimeInput(attrs={'type': 'datetime-local'})
        }
