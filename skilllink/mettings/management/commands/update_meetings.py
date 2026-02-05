from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import uuid
from ...models import Booking
from django.urls import reverse

class Command(BaseCommand):
    help = "Update meetings: generate links and auto-complete"

    def handle(self, *args, **kwargs):
        from skilllink.zoom_utils import get_zoom_meeting_status
        from accounts.models import Transaction, Notification
        now = timezone.now()

        # Generate meeting links 5 min before start (Legacy logic, keeping for fallback)
        for booking in Booking.objects.filter(status='scheduled', meeting_link__isnull=True):
            if booking.proposed_time:
                if now >= booking.proposed_time - timedelta(minutes=5):
                    booking.meeting_link = f"/meetings/booking/{booking.id}/" # Internal link as fallback
                    booking.save()
                    self.stdout.write(self.style.SUCCESS(f"Generated fallback link for booking {booking.id}"))

        # Strict Completion Rule: Both joined + 45 minutes passed
        for booking in Booking.objects.filter(status='scheduled', tokens_released=False, actual_start_time__isnull=False):
            if now >= booking.actual_start_time + timedelta(minutes=45):
                 # Commission logic (70/30 split)
                commission = int(booking.tokens_spent * 0.3)
                provider_total = booking.tokens_spent - commission
                
                booking.provider.add_tokens(
                    provider_total,
                    transaction_type='earned',
                    description=f"Payment for booking {booking.skill.name} (auto-completed 45m)"
                )
                
                # Notify Provider
                Notification.objects.create(
                    user=booking.provider.user,
                    title="Meeting Completed & Paid",
                    body=f"You earned {provider_total} tokens for {booking.skill.name}.",
                    link=f"/meetings/booking/{booking.id}/"
                )

                booking.status = 'completed'
                booking.tokens_released = True
                booking.review_pending = True
                booking.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f"Auto-completed booking {booking.id} (Both joined + 45m passed)."
                ))
                continue # Skip the zoom check for this booking

        # Poll Zoom status for others (fallback or if start time not tracked correctly)
        for booking in Booking.objects.filter(status='scheduled', zoom_meeting_id__isnull=False, tokens_released=False, actual_start_time__isnull=True):
            try:
                zoom_status = get_zoom_meeting_status(booking.zoom_meeting_id)
                
                # If meeting has finished, or if it's 2 hours past proposed time
                is_finished = (zoom_status == 'finished')
                overdue = (booking.proposed_time and now >= booking.proposed_time + timedelta(hours=2))
                
                if is_finished or overdue:
                    # Commission logic (70/30 split as per views.py)
                    commission = int(booking.tokens_spent * 0.3)
                    provider_total = booking.tokens_spent - commission
                    
                    booking.provider.add_tokens(
                        provider_total,
                        transaction_type='earned',
                        description=f"Payment for booking {booking.skill.name} (auto-completed)"
                    )
                    
                    booking.status = 'completed'
                    booking.tokens_released = True
                    booking.review_pending = True
                    booking.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"Auto-completed booking {booking.id} and transferred {provider_total} tokens."
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating booking {booking.id}: {e}"))

        # Legacy completion logic for those without Zoom ID
        for booking in Booking.objects.filter(status='scheduled', zoom_meeting_id__isnull=True, tokens_released=False):
            if booking.proposed_time:
                if now >= booking.proposed_time + timedelta(hours=1):
                    commission = int(booking.tokens_spent * 0.3)
                    provider_total = booking.tokens_spent - commission
                    
                    booking.provider.add_tokens(
                        provider_total,
                        transaction_type='earned',
                        description=f"Payment for booking {booking.skill.name} (legacy auto-completed)"
                    )
                    
                    booking.status = 'completed'
                    booking.tokens_released = True
                    booking.review_pending = True
                    booking.save()
                    self.stdout.write(self.style.SUCCESS(f"Legacy auto-completed booking {booking.id}"))
