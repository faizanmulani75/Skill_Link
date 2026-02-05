from django.db import models
from accounts.models import Profile
from skills.models import Skill
from django.utils import timezone

# ---------------- BOOKING ----------------
class Booking(models.Model):
    requester = models.ForeignKey(Profile, related_name='bookings_made', on_delete=models.CASCADE)
    provider = models.ForeignKey(Profile, related_name='bookings_received', on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=10, choices=[
        ('pending','Pending'),
        ('accepted','Accepted'),
        ('rejected','Rejected'),
        ('scheduled','Scheduled'),
        ('cancelled','Cancelled'),
        ('completed','Completed')],
        default='pending'
    )

    tokens_spent = models.PositiveIntegerField(default=0)
    tokens_deducted = models.BooleanField(default=False)
    tokens_scheduled_given = models.BooleanField(default=False)
    tokens_completed_given = models.BooleanField(default=False)

    proposed_time = models.DateTimeField(null=True, blank=True)
    meeting_link = models.URLField(null=True, blank=True)
    host_link = models.URLField(null=True, blank=True)
    
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    meeting_started = models.BooleanField(default=False)
    meeting_started_at = models.DateTimeField(null=True, blank=True)
    zoom_meeting_id = models.CharField(max_length=100, blank=True, null=True)
    review_pending = models.BooleanField(default=False)
    tokens_released = models.BooleanField(default=False) 
    times_taught_incremented = models.BooleanField(default=False)
    requester_joined = models.BooleanField(default=False)
    provider_joined = models.BooleanField(default=False)
    actual_start_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.requester.user.username} booked {self.skill.name} from {self.provider.user.username}"


# ---------------- REVIEW ----------------
class Review(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveIntegerField() # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for Booking {self.booking.id}"


# ---------------- REPORT ----------------
class Report(models.Model):
    reporter = models.ForeignKey(Profile, related_name='reports_sent', on_delete=models.CASCADE)
    reported_profile = models.ForeignKey(Profile, related_name='reports_received', on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    reason = models.TextField()
    admin_action_message = models.TextField(blank=True, null=True, help_text="Type a message here to send to the reporter upon saving.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.user.username} against {self.reported_profile.user.username}"


# ---------------- BOOKING HISTORY ----------------
class BookingHistory(models.Model):
    booking = models.ForeignKey(Booking, related_name="history", on_delete=models.CASCADE)
    proposer = models.ForeignKey(Profile, on_delete=models.CASCADE)
    proposed_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking {self.booking.id} proposed {self.proposed_time} by {self.proposer.user.username}"


# ---------------- CHAT MESSAGES ----------------
class Message(models.Model):
    booking = models.ForeignKey(Booking, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.sender.user.username} in Booking {self.booking.id}"

# ---------------- SKILL SWAP ----------------
class SwapRequest(models.Model):
    requester = models.ForeignKey(Profile, related_name='sent_swaps', on_delete=models.CASCADE)
    target = models.ForeignKey(Profile, related_name='received_swaps', on_delete=models.CASCADE)
    
    # The skill the requester WANTS (Target's skill)
    target_skill = models.ForeignKey(Skill, related_name='swaps_as_target', on_delete=models.CASCADE)
    
    # The skill the requester OFFERS (Requester's skill)
    requester_skill = models.ForeignKey(Skill, related_name='swaps_as_offered', on_delete=models.CASCADE)
    
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Swap: {self.requester} (offers {self.requester_skill}) <-> {self.target} (offers {self.target_skill})"
# ---------------- SIGNALS ----------------
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Booking)
def release_tokens_on_completion(sender, instance, created, **kwargs):
    """
    Automatically release tokens when a booking is marked as 'completed'.
    This ensures tokens are transferred even if the status is changed via Django Admin.
    """
    if instance.status == 'completed' and not instance.tokens_released:
        # Calculate split (70% to provider, 30% commission)
        commission = int(instance.tokens_spent * 0.3)
        provider_total = instance.tokens_spent - commission

        # Transfer tokens to provider
        instance.provider.add_tokens(
            provider_total,
            transaction_type='earned',
            description=f"Payment for booking {instance.skill.name} (auto-completed)"
        )

        # Mark as released to prevent double payment
        instance.tokens_released = True
        instance.review_pending = True
        
        # Save only the specific fields to avoid recursion loops
        instance.save(update_fields=['tokens_released', 'review_pending'])