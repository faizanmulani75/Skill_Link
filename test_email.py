import os
import sys
import django
from django.core.mail import send_mail
from django.conf import settings

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'skilllink'))

# Mock Redis URL to prevent settings import crash if missing
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skilllink.settings')
django.setup()

try:
    print(f"Attempting to send email with user: {settings.EMAIL_HOST_USER}")
    send_mail(
        'Test Email',
        'This is a test email to verify SMTP configuration.',
        settings.EMAIL_HOST_USER,
        ['skilllinproj@gmail.com'], # Sending to self for test
        fail_silently=False,
    )
    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Error sending email: {e}")
