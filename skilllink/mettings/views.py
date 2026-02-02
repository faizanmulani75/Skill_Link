from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile, Transaction
from skills.models import Skill, ProfileSkill
from .models import Booking, BookingHistory, Message, Report, SwapRequest
from skilllink.zoom_utils import create_zoom_meeting, get_zoom_meeting_status
import uuid
from datetime import datetime

# ------------------ CREATE BOOKING ------------------
@login_required
def create_booking(request, skill_id, provider_id):
    requester = request.user.profile
    skill = get_object_or_404(Skill, id=skill_id)
    provider = get_object_or_404(Profile, id=provider_id)

    if requester == provider:
        messages.error(request, "You cannot book your own skill.")
        return redirect('index')

    # Check if provider teaches this skill
    profile_skill = ProfileSkill.objects.filter(profile=provider, skill=skill).first()
    if not profile_skill:
        messages.error(request, "This provider does not offer this skill.")
        return redirect('index')

    tokens_needed = profile_skill.token_cost

    # Prevent duplicate pending bookings
    if Booking.objects.filter(
        requester=requester,
        provider=provider,
        skill=skill,
        status__in=['pending', 'accepted', 'scheduled']
    ).exists():
        messages.info(request, "You already have a booking request for this skill.")
        return redirect('booking_list')

    # Deduct tokens atomically
    try:
        with transaction.atomic():
            if requester.token_balance < tokens_needed:
                messages.error(request, "Insufficient tokens to book this skill.")
                return redirect('index')

            # Deduct tokens
            requester.deduct_tokens(tokens_needed, description=f"Booking for {skill.name}")

            # Create booking
            booking = Booking.objects.create(
                requester=requester,
                provider=provider,
                skill=skill,
                tokens_spent=tokens_needed,
                tokens_deducted=True,
                status='pending'
            )

        messages.success(request, f"Booking request sent. {tokens_needed} tokens deducted.")
        return redirect('booking_success')
    except Exception as e:
        messages.error(request, f"Failed to create booking: {e}")
        return redirect('index')


def finalize_booking(booking):
    if booking.tokens_released:
        return
    
    # Just update the status; the post_save signal will handle token transfer
    booking.status = 'completed'
    booking.save()


# ------------------ LIST BOOKINGS ------------------
@login_required
def booking_list(request):
    profile = request.user.profile
    now = timezone.now()

    # Proactive completion check for meetings that are overdue
    # Proactive completion check: Zoom status OR Overdue
    
    # 1. Check active scheduled meetings (started)
    active_bookings = Booking.objects.filter(
        status='scheduled', 
        tokens_released=False,
        meeting_started=True
    )

    for booking in active_bookings:
        should_complete = False
        
        # Check Zoom Status
        if booking.zoom_meeting_id:
            status = get_zoom_meeting_status(booking.zoom_meeting_id)
            if status == "finished":
                should_complete = True
        
        # Time-based fallback (2 hours after start)
        if not should_complete and booking.meeting_started_at:
             if now > booking.meeting_started_at + timezone.timedelta(hours=2):
                 should_complete = True
        
        if should_complete:
            finalize_booking(booking)

    # 2. Check strict overdue (fallback for when meeting_started was not set)
    overdue_bookings = Booking.objects.filter(
        status='scheduled', 
        tokens_released=False,
        proposed_time__lte=now - timezone.timedelta(hours=2)
    ).exclude(id__in=[b.id for b in active_bookings])
    
    for booking in overdue_bookings:
        finalize_booking(booking)

    bookings_received = Booking.objects.filter(provider=profile).order_by('-requested_at')
    bookings_made = Booking.objects.filter(requester=profile).order_by('-requested_at')
    return render(request, "booking_list.html", {
        "bookings_received": bookings_received,
        "bookings_made": bookings_made
    })


# ------------------ UPDATE BOOKING STATUS ------------------
@login_required
def booking_update_status(request, booking_id, action):
    booking = get_object_or_404(Booking, id=booking_id)
    user_profile = request.user.profile

    # Only provider or requester can update
    if user_profile not in [booking.provider, booking.requester]:
        messages.error(request, "You cannot modify this booking.")
        return redirect('booking_list')

    if action == "accept" and user_profile == booking.provider:
        booking.status = "accepted"
        booking.save()
        messages.success(request, "Booking accepted. Provider will schedule the meeting.")

    elif action == "reject" and user_profile == booking.provider:
        booking.status = "canceled"
        booking.save()
        booking.requester.add_tokens(
            booking.tokens_spent,
            transaction_type='refund',
            description=f"Refund for rejected booking {booking.skill.name}"
        )
        messages.info(request, "Booking rejected. Tokens refunded.")

    elif action == "cancel" and user_profile == booking.requester:
        booking.status = "canceled"
        booking.save()
        booking.requester.add_tokens(
            booking.tokens_spent,
            transaction_type='refund',
            description=f"Refund for canceled booking {booking.skill.name}"
        )
        messages.info(request, "Booking canceled. Tokens refunded.")

    else:
        messages.error(request, "Invalid action or permission.")
    return redirect('booking_list')


# ------------------ SCHEDULE MEETING ------------------
@login_required
def schedule_meeting(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, provider=request.user.profile)

    if request.method == "POST":
        proposed_time_str = request.POST.get("proposed_time")
        if not proposed_time_str:
            messages.error(request, "Select a valid time.")
            return redirect("schedule_meeting", booking_id=booking.id)

        try:
            proposed_time = datetime.strptime(proposed_time_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect("schedule_meeting", booking_id=booking.id)

        BookingHistory.objects.create(
            booking=booking,
            proposer=request.user.profile,
            proposed_time=proposed_time
        )

        booking.proposed_time = proposed_time
        booking.status = "scheduled"

        try:
            zoom_response = create_zoom_meeting(topic=f"{booking.skill.name} with {booking.provider.user.username}")
            booking.meeting_link = zoom_response.get("join_url")
            booking.zoom_meeting_id = zoom_response.get("id")
        except Exception as e:
            messages.error(request, f"Zoom error: {e}")

        booking.save()
        messages.success(request, "Meeting scheduled & Zoom link created.")
        return redirect("booking_list")

    history = BookingHistory.objects.filter(booking=booking).order_by("proposed_time")
    return render(request, "schedule_meeting.html", {"booking": booking, "history": history})


# ------------------ START MEETING ------------------
from django.utils import timezone
@login_required
def start_meeting(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Only requester or provider can join/start
    if request.user.profile not in [booking.requester, booking.provider]:
        messages.error(request, "You are not allowed to join this meeting.")
        return redirect('booking_list')

    # Create Zoom meeting if not exists
    if not booking.meeting_link:
        try:
            zoom_response = create_zoom_meeting(
                topic=f"{booking.skill.name} with {booking.provider.user.username}",
                duration=60  # in minutes (optional)
            )
            booking.meeting_link = zoom_response.get("join_url")
            booking.zoom_meeting_id = zoom_response.get("id")
            booking.meeting_started = True
            booking.meeting_started_at = timezone.now()
            booking.save()
            messages.success(request, "Zoom meeting created. You can join now.")
        except Exception as e:
            messages.error(request, f"Zoom error: {e}")
            return redirect('booking_list')

    # Mark meeting as started
    if not booking.meeting_started:
        booking.meeting_started = True
        booking.meeting_started_at = timezone.now()
        booking.save()

    return redirect(booking.meeting_link)


# ------------------ COMPLETE MEETING ------------------
@login_required
def complete_meeting(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, provider=request.user.profile)

    if booking.status != "scheduled":
        messages.error(request, "Cannot complete meeting that is not scheduled.")
        return redirect("dashboard")

    if not booking.tokens_released:
        commission = int(booking.tokens_spent * 0.3)
        provider_total = booking.tokens_spent - commission

        booking.provider.add_tokens(
            provider_total,
            transaction_type='earned',
            description=f"Payment for booking {booking.skill.name} (after commission)"
        )

        booking.tokens_released = True
        booking.status = "completed"
        booking.save()
        messages.success(request, f"Meeting completed. Provider received {provider_total} tokens.")
    else:
        messages.info(request, "Tokens already released.")

    return redirect("dashboard")

@login_required
def submit_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, requester=request.user.profile)
    
    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment", "")
        
        if rating:
            rating = int(rating)
            from .models import Review
            from django.db.models import Avg
            from skills.models import ProfileSkill

            # Create the review
            try:
                Review.objects.create(
                    booking=booking,
                    rating=rating,
                    comment=comment
                )
            except Exception: # Handle IntegrityError (duplicate) or other issues
                # If review exists (likely from previous failed attempt), we proceed.
                # We assume XP might have failed, so we add it manually here to recover.
                booking.provider.add_experience(rating * 10)
                booking.provider.save()
                pass
            booking.review_pending = False
            
            # Auto-transfer tokens if not already released
            if not booking.tokens_released:
                commission = int(booking.tokens_spent * 0.3)
                provider_total = booking.tokens_spent - commission
                
                booking.provider.add_tokens(
                    provider_total,
                    transaction_type='earned',
                    description=f"Payment for {booking.skill.name} (Review submitted)"
                )
                booking.tokens_released = True
                booking.status = 'completed'
            
            booking.save()

            # Update Profile Skill Average Rating
            profile_skill = ProfileSkill.objects.filter(profile=booking.provider, skill=booking.skill).first()
            if profile_skill:
                avg_skill_rating = Review.objects.filter(
                    booking__provider=booking.provider, 
                    booking__skill=booking.skill
                ).aggregate(Avg('rating'))['rating__avg']
                profile_skill.average_rating = avg_skill_rating or 0.0
                profile_skill.save()

            # Update Overall Profile Rating
            profile = booking.provider
            avg_profile_rating = Review.objects.filter(booking__provider=profile).aggregate(Avg('rating'))['rating__avg']
            profile.rating = avg_profile_rating or 0.0
            profile.save()

            messages.success(request, "Review submitted successfully!")
        else:
            messages.error(request, "Rating is required.")
            
    return redirect("booking_list")

@login_required
def rate_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, requester=request.user.profile)
    if not booking.review_pending:
        messages.info(request, "You have already reviewed this session.")
        return redirect("booking_list")
    return render(request, "rate_skill.html", {"booking": booking})

@login_required
def submit_report(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.user.profile != booking.requester:
        messages.error(request, "You are not authorized to report this session.")
        return redirect('booking_list')

    if request.method == "POST":
        reason = request.POST.get("reason")
        if reason:
            from .models import Report
            Report.objects.create(
                reporter=request.user.profile,
                reported_profile=booking.provider,
                booking=booking,
                reason=reason
            )
            messages.success(request, "Report submitted successfully. We will look into it.")
        else:
            messages.error(request, "Reason is required for reporting.")

    return redirect("booking_list")

def booking_success(request):
    return render(request, "booking_success.html")

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Booking, BookingHistory

@login_required
def booking_details(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    # Only allow requester or provider to view
    if request.user.profile not in [booking.requester, booking.provider]:
        messages.error(request, "You are not allowed to view this booking.")
        return redirect('booking_list')

    # Fetch all proposed times
    history = BookingHistory.objects.filter(booking=booking).order_by('proposed_time')
    chat_messages = Message.objects.filter(booking=booking).order_by('timestamp')

    return render(request, 'booking_details.html', {
        'booking': booking,
        'history': history,
        'chat_messages': chat_messages,
    })

from django.http import JsonResponse

@login_required
def send_message(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user.profile not in [booking.requester, booking.provider]:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            message = Message.objects.create(
                booking=booking,
                sender=request.user.profile,
                content=content
            )
            return JsonResponse({
                'status': 'success',
                'message': {
                    'sender': message.sender.user.username,
                    'content': message.content,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                }
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def get_messages(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user.profile not in [booking.requester, booking.provider]:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    messages_list = Message.objects.filter(booking=booking).order_by('timestamp')
    data = []
    for msg in messages_list:
        data.append({
            'sender': msg.sender.user.username,
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_me': msg.sender == request.user.profile
        })
    return JsonResponse({'status': 'success', 'messages': data})

@login_required
def user_reports(request):
    profile = request.user.profile
    # Reports filed by the user
    reports_filed = Report.objects.filter(reporter=profile).order_by('-created_at')
    # Reports filed against the user
    reports_against = Report.objects.filter(reported_profile=profile).order_by('-created_at')
    
    # Reviews given by the user (as requester)
    from .models import Review
    reviews_given = Review.objects.filter(booking__requester=profile).select_related('booking', 'booking__provider').order_by('-created_at')
    
    # Reviews received by the user (as provider)
    reviews_received = Review.objects.filter(booking__provider=profile).select_related('booking', 'booking__requester').order_by('-created_at')
    
    return render(request, 'user_reports.html', {
        'reports_filed': reports_filed,
        'reports_against': reports_against,
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
    })

# ------------------ SKILL SWAP ------------------
@login_required
def request_swap(request, skill_id, provider_id):
    requester = request.user.profile
    target = get_object_or_404(Profile, id=provider_id)
    target_skill = get_object_or_404(Skill, id=skill_id)

    if requester == target:
        messages.error(request, "You cannot swap with yourself.")
        return redirect('index')

    if request.method == "POST":
        requester_skill_id = request.POST.get("offered_skill_id")
        requester_skill = get_object_or_404(Skill, id=requester_skill_id)
        
        # Check if already requested
        if SwapRequest.objects.filter(requester=requester, target=target, target_skill=target_skill, status='pending').exists():
             messages.info(request, "Swap request already pending.")
             return redirect('booking_list')

        SwapRequest.objects.create(
            requester=requester,
            target=target,
            target_skill=target_skill,
            requester_skill=requester_skill
        )
        messages.success(request, "Swap request sent!")
        return redirect('booking_list')

    # Get skills the requester can offer (that match what the target wants)
    from skills.models import ProfileSkill
    
    # 1. Get all skills the requester is teaching
    requester_teaching_skills = ProfileSkill.objects.filter(profile=requester, available_for_teaching=True).select_related('skill')
    
    # 2. Determine acceptable skills (Specific > Global)
    target_profile_skill = ProfileSkill.objects.filter(profile=target, skill=target_skill).first()
    
    specific_prefs = target_profile_skill.desired_exchange_skills.all() if target_profile_skill else []
    
    if specific_prefs:
        # Strict matching if specific preferences exist
        acceptable_skill_ids = [s.id for s in specific_prefs]
        match_source = "specific"
    else:
        # No specific preferences -> Strict! No swaps allowed unless specified
        acceptable_skill_ids = []
        match_source = "none_set"

    matching_skills = requester_teaching_skills.filter(skill__id__in=acceptable_skill_ids)
    
    return render(request, "swap_request_form.html", {
        "target": target,
        "target_skill": target_skill,
        "my_skills": matching_skills,
        "has_match": matching_skills.exists(),
        "match_source": match_source,
        "specific_prefs": specific_prefs
    })

@login_required
def manage_swap_requests(request):
    profile = request.user.profile
    received_swaps = SwapRequest.objects.filter(target=profile).order_by('-created_at')
    sent_swaps = SwapRequest.objects.filter(requester=profile).order_by('-created_at')
    
    return render(request, "swap_list.html", {
        "received_swaps": received_swaps,
        "sent_swaps": sent_swaps
    })

@login_required
def respond_to_swap(request, swap_id, action):
    swap = get_object_or_404(SwapRequest, id=swap_id, target=request.user.profile)
    
    if action == "accept":
        try:
            with transaction.atomic():
                 # 1. Requester -> Target (for Target's skill)
                 ps1 = ProfileSkill.objects.filter(profile=swap.target, skill=swap.target_skill).first()
                 cost1 = ps1.token_cost if ps1 else 0
                 
                 if swap.requester.tokens_balance < cost1:
                     messages.error(request, f"{swap.requester.user.username} has insufficient tokens for swap.")
                     return redirect('manage_swap_requests')
                 
                 # Deduct from Requester
                 swap.requester.deduct_tokens(cost1, f"Swap booking for {swap.target_skill.name}")

                 Booking.objects.create(
                     requester=swap.requester,
                     provider=swap.target,
                     skill=swap.target_skill,
                     status='accepted',
                     tokens_spent=cost1,
                     tokens_deducted=True
                 )

                 # 2. Target -> Requester (for Requester's skill)
                 ps2 = ProfileSkill.objects.filter(profile=swap.requester, skill=swap.requester_skill).first()
                 cost2 = ps2.token_cost if ps2 else 0
                 
                 if swap.target.tokens_balance < cost2:
                      messages.error(request, "You have insufficient tokens to accept this swap.")
                      # Transaction atomic will rollback the first deduction
                      raise Exception("Insufficient tokens")
                 
                 # Deduct from Target
                 swap.target.deduct_tokens(cost2, f"Swap booking for {swap.requester_skill.name}")

                 Booking.objects.create(
                     requester=swap.target,
                     provider=swap.requester,
                     skill=swap.requester_skill,
                     status='accepted', 
                     tokens_spent=cost2,
                     tokens_deducted=True
                 )

                 swap.status = 'accepted'
                 swap.save()
                 messages.success(request, "Swap accepted! Two bookings created.")
        except Exception as e:
            if str(e) != "Insufficient tokens":
                messages.error(request, f"Error processing swap: {e}")
             
    elif action == "reject":
        swap.status = 'rejected'
        swap.save()
        messages.info(request, "Swap request rejected.")
        
    return redirect('manage_swap_requests')
