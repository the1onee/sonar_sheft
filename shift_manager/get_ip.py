#!/usr/bin/env python
"""
سكريبت بسيط لمعرفة IP الخاص بك على الشبكة المحلية
"""
import socket
import platform

def get_local_ip():
    """الحصول على IP المحلي"""
    try:
        # إنشاء socket للحصول على IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # لا نحتاج للاتصال فعلياً، فقط نحتاج لمعرفة IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "غير متصل بالشبكة"

def main():
    print("=" * 60)
    print("        معلومات الاتصال بالشبكة المحلية")
    print("=" * 60)
    print()
    
    ip = get_local_ip()
    hostname = socket.gethostname()
    
    print(f"🖥️  اسم الجهاز: {hostname}")
    print(f"📡 IP Address: {ip}")
    print()
    print("=" * 60)
    print("📱 للوصول من أجهزة أخرى في نفس الشبكة:")
    print("=" * 60)
    print()
    print(f"   استخدم هذا الرابط: http://{ip}:8000")
    print()
    print("💡 ملاحظات:")
    print("  • تأكد أن جميع الأجهزة على نفس الشبكة (نفس WiFi)")
    print("  • قد يحتاج Firewall إلى السماح بالمنفذ 8000")
    print("  • على Windows: افتح Firewall وأضف استثناء للمنفذ 8000")
    print()
    
    # معلومات إضافية لـ Windows
    if platform.system() == "Windows":
        print("⚙️  لفتح المنفذ في Windows Firewall:")
        print("  1. ابحث عن 'Windows Defender Firewall'")
        print("  2. اختر 'Advanced settings'")
        print("  3. اختر 'Inbound Rules' → 'New Rule'")
        print("  4. اختر 'Port' → Next")
        print("  5. اختر TCP وأدخل 8000 → Next")
        print("  6. اختر 'Allow the connection' → Finish")
        print()
    
    print("=" * 60)

if __name__ == "__main__":
    main()

