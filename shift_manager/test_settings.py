import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shift_manager.settings')

import django
django.setup()

from django.conf import settings

print("=" * 60)
print("ALLOWED_HOSTS:")
print(settings.ALLOWED_HOSTS)
print("=" * 60)
print("DEBUG:", settings.DEBUG)
print("SECRET_KEY:", settings.SECRET_KEY[:20] + "...")
print("=" * 60)

