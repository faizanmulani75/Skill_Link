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
    
    def __str__(self):
        return self.user.username
    
    def calculate_level(self):
        """Calculate level based on experience points"""
        xp = self.experience_points
        
        # Level thresholds
        if xp < 100:
            return 1
        elif xp < 250:
            return 2
        elif xp < 500:
            return 3
        elif xp < 1000:
            return 4
        elif xp < 2000:
            return 5
        elif xp < 3500:
            return 6
        elif xp < 5500:
            return 7
        elif xp < 8500:
            return 8
        elif xp < 12500:
            return 9
        else:
            return 10  # Max level
    
    def get_xp_for_level(self, level):
        """Get XP required to reach a specific level"""
        thresholds = {
            1: 0,
            2: 100,
            3: 250,
            4: 500,
            5: 1000,
            6: 2000,
            7: 3500,
            8: 5500,
            9: 8500,
            10: 12500
        }
        return thresholds.get(level, 0)
    
    def get_level_progress(self):
        """Get progress to next level as a percentage"""
        current_level = self.level
        
        if current_level >= 10:
            return 100  # Max level reached
        
        current_xp = self.experience_points
        current_level_xp = self.get_xp_for_level(current_level)
        next_level_xp = self.get_xp_for_level(current_level + 1)
        
        xp_in_current_level = current_xp - current_level_xp
        xp_needed_for_next = next_level_xp - current_level_xp
        
        if xp_needed_for_next == 0:
            return 100
        
        progress = (xp_in_current_level / xp_needed_for_next) * 100
        return min(100, max(0, progress))
    
    def add_experience(self, xp_amount):
        """Add experience points and update level"""
        old_level = self.level
        self.experience_points += xp_amount
        new_level = self.calculate_level()
        
        if new_level != old_level:
            self.level = new_level
            # Handle Level Up side effects (Notifications, Rewards)
            self.on_level_up(old_level, new_level)
            return True  # Level up occurred
        
        return False  # No level up

    def on_level_up(self, old_level, new_level):
        """Handle actions when a user levels up"""
        from accounts.models import Notification  # Avoid circular import at top

        # 1. Standard Level Up Notification
        Notification.objects.create(
            user=self.user,
            title=f"🎉 Level Up! You're now Level {new_level}!",
            body=f"Congratulations! You've reached Level {new_level}.",
            link="/accounts/dashboard/"
        )

        # 2. Milestone Reward (Every 5 Levels)
        if new_level % 5 == 0:
            reward_tokens = 50
            self.add_tokens(
                amount=reward_tokens,
                description=f"Level {new_level} Milestone Reward",
                transaction_type="earned"
            )
            
            # Milestone Notification
            Notification.objects.create(
                user=self.user,
                title="🎁 Milestone Reward!",
                body=f"You've received {reward_tokens} tokens for reaching Level {new_level}!",
                link="/accounts/dashboard/"
            )

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
