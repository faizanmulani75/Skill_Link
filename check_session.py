import os
import sys
import django
from django.conf import settings

# Add project root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'skilllink'))

# Mock Redis URL to prevent settings import crash if missing
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skilllink.settings')

django.setup()

from django.contrib.sessions.models import Session
from accounts.models import Profile

session_key = 'l3j34kvblpu8p9rtq1whs8rfud8ofe3l'

try:
    s = Session.objects.get(session_key=session_key)
    print(f"✅ Session FOUND: {session_key}")
    print(f"   Expire date: {s.expire_date}")
    
    decoded = s.get_decoded()
    uid = decoded.get('_auth_user_id')
    print(f"   User ID: {uid}")
    
    if uid:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(pk=uid)
            print(f"   Username: {user.username}")
        except Exception as e:
            print(f"   ❌ User lookup failed: {e}")
            
except Session.DoesNotExist:
    print(f"❌ Session NOT FOUND in DB: {session_key}")
    print("This means the browser has a cookie, but the database doesn't know about it.")
    print("Recommendation: Clear cookies and log in again.")
