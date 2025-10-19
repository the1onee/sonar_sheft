from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import EmployeeAssignment
from .forms import EmployeeAssignmentForm

def home(request):
    if request.method == "POST":
        form = EmployeeAssignmentForm(request.POST)
        if form.is_valid():
            employee = form.cleaned_data['employee']
            assigned_at = form.cleaned_data['assigned_at']
            today = assigned_at.date()

            # التحقق إذا تم إسناد الموظف في أي شفت اليوم
            exists = EmployeeAssignment.objects.filter(
                employee=employee,
                assigned_at__date=today
            ).exists()

            if exists:
                messages.error(request, f"الموظف {employee.name} تم إسناده اليوم مسبقًا!")
            else:
                form.save()
                messages.success(request, f"تم إسناد الموظف {employee.name} بنجاح!")

            return redirect('home')
    else:
        form = EmployeeAssignmentForm()

    assignments = EmployeeAssignment.objects.order_by('-assigned_at')[:20]
    total_employees = EmployeeAssignment.objects.values('employee').distinct().count()
    total_sonars = EmployeeAssignment.objects.values('sonar').distinct().count()

    return render(request, 'home.html', {
        'form': form,
        'assignments': assignments,
        'total_employees': total_employees,
        'total_sonars': total_sonars
    })
