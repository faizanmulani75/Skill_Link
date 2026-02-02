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
            Notification.objects.create(
                user=user_profile.user,
                title="Booking Update",
                body=msg,
                link="/meetings/"
            )

@receiver(post_save, sender=Profile)
def broadcast_token_update(sender, instance, **kwargs):
    # This might be noisy if updated frequently, but good for real-time balance
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{instance.user.id}",
        {
            "type": "token_update",
            "balance": instance.token_balance
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
