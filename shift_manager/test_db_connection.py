#!/usr/bin/env python
"""
سكريبت لاختبار الاتصال بقاعدة البيانات
يمكن استخدامه للتحقق من إعدادات PostgreSQL أو SQLite
"""
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')
django.setup()

from django.db import connection
from django.conf import settings

def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    print("=" * 60)
    print("🔍 اختبار الاتصال بقاعدة البيانات")
    print("=" * 60)
    
    # عرض نوع قاعدة البيانات
    db_engine = settings.DATABASES['default']['ENGINE']
    
    if 'postgresql' in db_engine:
        print("\n📊 نوع القاعدة: PostgreSQL")
        print(f"   الاسم: {settings.DATABASES['default']['NAME']}")
        print(f"   المستخدم: {settings.DATABASES['default']['USER']}")
        print(f"   المضيف: {settings.DATABASES['default']['HOST']}")
        print(f"   المنفذ: {settings.DATABASES['default']['PORT']}")
    elif 'sqlite' in db_engine:
        print("\n📊 نوع القاعدة: SQLite")
        print(f"   الملف: {settings.DATABASES['default']['NAME']}")
    else:
        print(f"\n📊 نوع القاعدة: {db_engine}")
    
    # محاولة الاتصال
    try:
        print("\n⏳ جاري الاتصال بقاعدة البيانات...")
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result:
            print("✅ نجح الاتصال بقاعدة البيانات!")
            
            # عرض معلومات إضافية
            if 'postgresql' in db_engine:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                print(f"\n📌 إصدار PostgreSQL:")
                print(f"   {version}")
            
            # عرض عدد الجداول
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """ if 'postgresql' in db_engine else """
                SELECT COUNT(*) 
                FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            table_count = cursor.fetchone()[0]
            print(f"\n📋 عدد الجداول: {table_count}")
            
            if table_count == 0:
                print("\n⚠️  لم يتم تطبيق migrations بعد!")
                print("   قم بتشغيل: python manage.py migrate")
            else:
                print("\n✅ تم تطبيق migrations بنجاح")
            
        cursor.close()
        
    except Exception as e:
        print(f"\n❌ فشل الاتصال بقاعدة البيانات!")
        print(f"   الخطأ: {str(e)}")
        print("\n💡 تأكد من:")
        if 'postgresql' in db_engine:
            print("   1. تشغيل خدمة PostgreSQL")
            print("   2. صحة اسم المستخدم وكلمة المرور")
            print("   3. وجود قاعدة البيانات")
            print("   4. صحة عنوان المضيف والمنفذ")
        else:
            print("   1. وجود مجلد المشروع")
            print("   2. الصلاحيات اللازمة لإنشاء/قراءة الملف")
        
        return False
    
    print("\n" + "=" * 60)
    return True


if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)

