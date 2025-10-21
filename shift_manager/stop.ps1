#!/usr/bin/env pwsh
# ========================================
#  إيقاف نظام السونار - PowerShell
# ========================================

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   إيقاف نظام السونار" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. إيقاف جميع عمليات Python
Write-Host "[1/4] إيقاف جميع عمليات Python..." -ForegroundColor White
try {
    Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "   ✓ تم إيقاف Python" -ForegroundColor Green
} catch {
    Write-Host "   ✓ لا توجد عمليات Python نشطة" -ForegroundColor Gray
}

# 2. إيقاف Celery
Write-Host "[2/4] إيقاف Celery..." -ForegroundColor White
try {
    Get-Process -Name celery -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "   ✓ تم إيقاف Celery" -ForegroundColor Green
} catch {
    Write-Host "   ✓ لا توجد عمليات Celery نشطة" -ForegroundColor Gray
}

# 3. تحرير البورت 8000
Write-Host "[3/4] تحرير البورت 8000..." -ForegroundColor White
try {
    $connections = netstat -ano | Select-String ":8000.*LISTENING"
    if ($connections) {
        foreach ($conn in $connections) {
            $pid = ($conn -split '\s+')[-1]
            if ($pid -match '^\d+$') {
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
        Write-Host "   ✓ تم تحرير البورت 8000" -ForegroundColor Green
    } else {
        Write-Host "   ✓ البورت 8000 غير مستخدم" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠ تحذير: قد يكون البورت محرراً بالفعل" -ForegroundColor Yellow
}

# 4. تنظيف
Write-Host "[4/4] تنظيف..." -ForegroundColor White
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   تم إيقاف جميع الخدمات بنجاح ✓" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# التحقق النهائي
Write-Host "التحقق النهائي:" -ForegroundColor Yellow
$pythonProcs = Get-Process -Name python -ErrorAction SilentlyContinue
$port8000 = netstat -ano | Select-String ":8000.*LISTENING"

if (-not $pythonProcs -and -not $port8000) {
    Write-Host "  ✓ لا توجد عمليات نشطة" -ForegroundColor Green
    Write-Host "  ✓ البورت 8000 خالي" -ForegroundColor Green
} else {
    if ($pythonProcs) {
        Write-Host "  ⚠ تحذير: لا زالت هناك عمليات Python نشطة ($($pythonProcs.Count))" -ForegroundColor Yellow
    }
    if ($port8000) {
        Write-Host "  ⚠ تحذير: البورت 8000 لا زال مستخدماً" -ForegroundColor Yellow
    }
}

Write-Host ""
Read-Host "اضغط Enter للخروج"

