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
        from accounts.models import Transaction
        now = timezone.now()

        # Generate meeting links 5 min before start (Legacy logic, keeping for fallback)
        for booking in Booking.objects.filter(status='scheduled', meeting_link__isnull=True):
            if booking.proposed_time:
                if now >= booking.proposed_time - timedelta(minutes=5):
                    booking.meeting_link = f"/meetings/booking/{booking.id}/" # Internal link as fallback
                    booking.save()
                    self.stdout.write(self.style.SUCCESS(f"Generated fallback link for booking {booking.id}"))

        # Poll Zoom status for scheduled meetings with Zoom ID
        for booking in Booking.objects.filter(status='scheduled', zoom_meeting_id__isnull=False, tokens_released=False):
            try:
                zoom_status = get_zoom_meeting_status(booking.zoom_meeting_id)
                
                # If meeting has finished, or if it's 2 hours past proposed time and we can't get status
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
