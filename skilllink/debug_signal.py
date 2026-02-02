import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skilllink.settings')
django.setup()

from accounts.models import Profile, User, Transaction
from skills.models import Skill
from mettings.models import Booking

def run_debug():
    print("--- Starting Debug ---")
    
    # Ensure users exist
    provider_user, _ = User.objects.get_or_create(username='debug_provider')
    requester_user, _ = User.objects.get_or_create(username='debug_requester')
    
    provider, _ = Profile.objects.get_or_create(user=provider_user)
    requester, _ = Profile.objects.get_or_create(user=requester_user)
    
    # Ensure skill exists
    skill, _ = Skill.objects.get_or_create(name='Debug Skill')
    
    # Cleanup previous transactions for clean state
    Transaction.objects.filter(user=provider).delete()
    provider.tokens_balance = 0
    provider.save()
    
    print(f"Initial Provider Balance: {provider.tokens_balance}")
    
    # Create Booking
    booking = Booking.objects.create(
        requester=requester,
        provider=provider,
        skill=skill,
        tokens_spent=100,
        status='pending'
    )
    print(f"Created Booking {booking.id} with status: {booking.status}")
    
    # Simulate Admin Action: Update status to completed
    print("Updating status to 'completed'...")
    booking.status = 'completed'
    booking.save() # This should trigger the signal
    
    # Refresh objects
    booking.refresh_from_db()
    provider.refresh_from_db()
    
    print(f"Booking Status: {booking.status}")
    print(f"Tokens Released Flag: {booking.tokens_released}")
    print(f"Provider Balance (from DB field): {provider.tokens_balance}")
    
    # Check Transactions
    txs = Transaction.objects.filter(user=provider)
    print(f"Transactions found: {txs.count()}")
    for tx in txs:
        print(f" - {tx.transaction_type}: {tx.amount}")

    if provider.tokens_balance == 70:
        print("SUCCESS: Tokens transferred correctly.")
    else:
        print("FAILURE: Tokens NOT transferred.")

if __name__ == '__main__':
    run_debug()
