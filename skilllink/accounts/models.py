from django.db import models, transaction as db_transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
import random
from datetime import datetime, timedelta
from cloudinary.models import CloudinaryField

class EmailOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.created_at = datetime.now()  # reset timestamp
        self.save()
        return self.otp

    def is_valid(self):
        """Check if OTP is still valid (2 minutes)"""
        if not self.otp:
            return False
        return datetime.now() <= self.created_at + timedelta(minutes=2)

    def __str__(self):
        return f"{self.user.username} OTP"

# ---------------- PROFILE ----------------

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.CharField(max_length=100 ,blank=True, null=True)
    profile_pic = CloudinaryField(
    'image',
    folder='profile_skills',
    blank=True,
    null=True,
    default="https://res.cloudinary.com/dctwxqpeo/image/upload/v1757868228/default_ehmhxs.png"
)

    location = models.CharField(max_length=100, blank=True, null=True)
    languages_spoken = models.CharField(max_length=200, blank=True, null=True)
    # experience_level = models.CharField(
    #     max_length=20,
    #     choices=[
    #         ("beginner", "Beginner"),
    #         ("intermediate", "Intermediate"),                         #future plan
    #         ("expert", "Expert"),
    #     ],
    #     default="beginner"
    # )
    tokens_balance = models.PositiveIntegerField(default=0)
    rating = models.FloatField(default=0.0)
    joined_on = models.DateTimeField(default=timezone.now)
    experience_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    verified = models.BooleanField(default=True)
    desired_skills = models.ManyToManyField('skills.Skill', related_name='wanted_by_profiles', blank=True)
    has_reviewed_platform = models.BooleanField(default=False)
    show_level_up_modal = models.BooleanField(default=False)
    blocked_until = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.user.username

    # --- Token-related calculations ---
    @property
    def total_earned(self):
        from mettings.models import Booking
        return Booking.objects.filter(provider=self, status="completed").aggregate(
            total=models.Sum("tokens_spent")
        )["total"] or 0

    @property
    def total_spent(self):
        from mettings.models import Booking
        return Booking.objects.filter(requester=self, status="completed").aggregate(
            total=models.Sum("tokens_spent")
        )["total"] or 0

    @property
    def total_purchased(self):
        from .models import Transaction
        return Transaction.objects.filter(user=self, transaction_type='purchased').aggregate(
            total=models.Sum("amount")
        )["total"] or 0


    @property
    def token_balance(self):
        from .models import Transaction
        totals = Transaction.objects.filter(user=self).values("transaction_type").annotate(total=models.Sum("amount"))
        data = {t["transaction_type"]: (t["total"] or 0) for t in totals}
        
        earned = data.get("earned", 0)
        spent = data.get("spent", 0)
        purchased = data.get("purchased", 0)
        refund = data.get("refund", 0)

        return (purchased + earned + refund) - spent




    def add_tokens(self, amount, description="Purchased tokens", transaction_type='purchased'):
        from .models import Transaction
        Transaction.objects.create(
            user=self,
            amount=amount,
            transaction_type=transaction_type,
            description=description
        )
        # Note: balance field is now updated via signal

    def deduct_tokens(self, amount, description="Spent tokens"):
        """Deduct tokens from the profile if balance is sufficient."""
        # Refresh profile to avoid stale balance
        self.refresh_from_db()

        if self.token_balance >= amount:
            from .models import Transaction
            Transaction.objects.create(
                user=self,   # Profile FK
                amount=amount,
                transaction_type="spent",
                description=description
            )
            # Note: balance field is now updated via signal
            return True
        return False


# --- Signals for Token Balance Sync ---

@receiver(post_save, sender='accounts.Transaction')
@receiver(post_delete, sender='accounts.Transaction')
def update_profile_token_balance(sender, instance, **kwargs):
    """
    Automatically synchronize the physical tokens_balance field 
    whenever a Transaction is created, updated, or deleted.
    """
    profile = instance.user
    # Recalculate and update the field
    profile.tokens_balance = profile.token_balance
    profile.save(update_fields=['tokens_balance'])




# ---------------- TRANSACTION ----------------
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('earned', 'Earned'),
        ('spent', 'Spent'),
        ('purchased', 'Purchased'),
        ('refund', 'Refund'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.transaction_type} {self.amount} tokens"

# ---------------- NOTIFICATION ----------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    body = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
