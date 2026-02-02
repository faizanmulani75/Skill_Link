from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Booking, Message, Review
from accounts.models import Profile, Notification

@receiver(post_save, sender=Message)
def broadcast_message(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        # Notify the specific chat room
        async_to_sync(channel_layer.group_send)(
            f"meeting_{instance.booking.id}",
            {
                "type": "chat_message",
                "message": {
                    "sender": instance.sender.user.username,
                    "content": instance.content,
                    "timestamp": instance.timestamp.isoformat()
                }
            }
        )
        # Persistent Notification
        recipient = instance.booking.provider if instance.sender == instance.booking.requester else instance.booking.requester
        Notification.objects.create(
            user=recipient.user,
            title="New Message",
            body=f"From {instance.sender.user.username}: {instance.content[:30]}...",
            link=f"/meetings/booking/{instance.booking.id}/"
        )

@receiver(post_save, sender=Booking)
def broadcast_booking_update(sender, instance, created, **kwargs):
    if created:
        # Persistent Notification
        Notification.objects.create(
            user=instance.provider.user,
            title="New Booking Request",
            body=f"You have a new request for {instance.skill.name}.",
            link="/meetings/"
        )
    else:
        # Notify requester/provider about status change
        for user_profile in [instance.requester, instance.provider]:
            msg = f"Booking for {instance.skill.name} is now {instance.status}."
            
            # 1. Persistent Notification (Database Store)
            Notification.objects.create(
                user=user_profile.user,
                title="Booking Update",
                body=msg,
                link="/meetings/"
            )

        # Increment times_taught if status is completed
        if instance.status == 'completed' and not instance.times_taught_incremented:
            from skills.models import ProfileSkill
            try:
                profile_skill = ProfileSkill.objects.get(profile=instance.provider, skill=instance.skill)
                profile_skill.times_taught += 1
                profile_skill.save()
                
                # Mark as incremented to prevent double counting
                Booking.objects.filter(pk=instance.pk).update(times_taught_incremented=True)
            except ProfileSkill.DoesNotExist:
                pass

        # Increment times_taught if status is completed
        if instance.status == 'completed' and not instance.times_taught_incremented:
            from skills.models import ProfileSkill
            try:
                profile_skill = ProfileSkill.objects.get(profile=instance.provider, skill=instance.skill)
                profile_skill.times_taught += 1
                profile_skill.save()
                
                # Mark as incremented to prevent double counting
                Booking.objects.filter(pk=instance.pk).update(times_taught_incremented=True)
            except ProfileSkill.DoesNotExist:
                pass

@receiver(post_save, sender=Profile)
def broadcast_token_update(sender, instance, **kwargs):
    # This might be noisy if updated frequently, but good for real-time balance
    channel_layer = get_channel_layer()
    print(f"DEBUG: Broadcasting token update for user {instance.user.id}, New Balance: {instance.tokens_balance}")
    async_to_sync(channel_layer.group_send)(
        f"user_{instance.user.id}",
        {
            "type": "token_update",
            "balance": instance.tokens_balance
        }
    )

@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{instance.user.id}",
            {
                "type": "notification",
                "notification": {
                    "id": instance.id,
                    "title": instance.title,
                    "body": instance.body,
                    "link": instance.link,
                    "timestamp": instance.timestamp.isoformat()
                }
            }
        )


# ---------------- REVIEW XP ----------------
@receiver(post_save, sender=Review)
def update_provider_xp(sender, instance, created, **kwargs):
    """
    Update provider's experience points and level when they receive a review.
    XP calculation: rating * 10 (e.g., 5 stars = 50 XP)
    """
    if created:
        provider = instance.booking.provider
        xp_earned = instance.rating * 10
        
        # Add experience and check for level up
        # Profile.add_experience now handles notifications internally
        provider.add_experience(xp_earned)
        provider.save()

# ---------------- REPORT BLOCKING ----------------
from .models import Report
from datetime import timedelta
from django.utils import timezone

@receiver(post_save, sender=Report)
def check_report_thresholds(sender, instance, created, **kwargs):
    if created:
        reported_profile = instance.reported_profile
        report_count = Report.objects.filter(reported_profile=reported_profile).count()

        block_days = 0
        if report_count == 3:
            block_days = 1
        elif report_count == 5:
            block_days = 3
        elif report_count == 7:
            block_days = 7
        elif report_count == 10:
            block_days = 15
        elif report_count >= 13: # 13+ reports catch-all or just 13? User said "13 reports 1 month". Assuming specific triggers. The user might want cumulative or recurring. Usually strictly equals is safer unless requested otherwise. Ill stick to == for 13, maybe >= 13 if they want consistent blocking. But user specified checkpoints.
             if report_count == 13:
                 block_days = 30
        
        if block_days > 0:
            reported_profile.blocked_until = timezone.now() + timedelta(days=block_days)
            reported_profile.save(update_fields=['blocked_until'])
            
            # Deactivate user to prevent new logins
            user = reported_profile.user
            user.is_active = False
            user.save(update_fields=['is_active'])
            
            # Notify the user (Persistent)
            Notification.objects.create(
                user=user,
                title="Account Temporarily Blocked",
                body=f"Due to receiving multiple reports ({report_count}), your account has been blocked for {block_days} day(s).",
                link="/accounts/login/" 
            )

            # 1. Kill invalid sessions (Backend Logout)
            from django.contrib.sessions.models import Session
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for session in sessions:
                data = session.get_decoded()
                if str(data.get('_auth_user_id')) == str(user.id):
                    session.delete()
            
            # 2. WebSocket Force Logout (Frontend Redirect)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "force_logout",
                    "message": f"You have been blocked for {block_days} days due to multiple reports."
                }
            )
